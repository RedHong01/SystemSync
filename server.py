#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import mimetypes
import os
from pathlib import Path
import platform
import re
import secrets
import shutil
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from project_packager import DEFAULT_EXCLUDES, Planner, copy_tree, write_reports


APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
CONFIG_PATH = APP_DIR / "config.json"
STATE_PATH = APP_DIR / "runtime-state.json"
APP_VERSION = "0.1.0"

DEFAULT_CONFIG = {
    "listen_host": "0.0.0.0",
    "listen_port": 8765,
    "local_name": "MacWorkstation",
    "remote_name": "WindowsWorkstation",
    "remote_ip": "",
    "remote_mac": "",
    "remote_agent_port": 8766,
    "remote_device_id": "",
    "local_device_id": "",
    "syncthing_folder_id": "lan-sync",
    "syncthing_url": "http://127.0.0.1:8384",
    "sync_root": str(Path.home() / "Sync"),
    "remote_project_base": "D:\\LanSyncProjects",
    "mac_ip": "",
    "mac_mac": "",
    "github_repo": "",
    "current_version": APP_VERSION,
    "shared_token": "",
}

CONFIG_LOCK = threading.Lock()
STATE_LOCK = threading.Lock()
JOBS_LOCK = threading.Lock()
JOBS = {}


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default.copy()


def save_json(path, value):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(path)


def load_config():
    with CONFIG_LOCK:
        config = DEFAULT_CONFIG.copy()
        config.update(load_json(CONFIG_PATH, {}))
        if not config.get("shared_token"):
            config["shared_token"] = secrets.token_urlsafe(32)
            save_json(CONFIG_PATH, config)
        return config


def update_config(patch):
    with CONFIG_LOCK:
        config = DEFAULT_CONFIG.copy()
        config.update(load_json(CONFIG_PATH, {}))
        allowed = {
            "local_name",
            "remote_name",
            "remote_ip",
            "remote_mac",
            "remote_agent_port",
            "remote_device_id",
            "local_device_id",
            "syncthing_folder_id",
            "sync_root",
            "remote_project_base",
            "mac_ip",
            "mac_mac",
            "github_repo",
            "current_version",
        }
        for key, value in patch.items():
            if key in allowed:
                config[key] = value
        if not config.get("shared_token"):
            config["shared_token"] = secrets.token_urlsafe(32)
        save_json(CONFIG_PATH, config)
        return config


def public_config(config):
    return {key: value for key, value in config.items() if key != "shared_token"}


def load_state():
    with STATE_LOCK:
        return load_json(STATE_PATH, {})


def update_state(patch):
    with STATE_LOCK:
        state = load_json(STATE_PATH, {})
        state.update(patch)
        save_json(STATE_PATH, state)
        return state


def syncthing_config_path():
    if platform.system() == "Darwin":
        return Path.home() / "Library/Application Support/Syncthing/config.xml"
    if platform.system() == "Windows":
        base = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData/Local"))
        return Path(base) / "Syncthing/config.xml"
    return Path.home() / ".local/state/syncthing/config.xml"


def syncthing_api_key():
    path = syncthing_config_path()
    try:
        root = ET.parse(path).getroot()
        value = root.findtext("./gui/apikey")
        return value or ""
    except (OSError, ET.ParseError):
        return ""


def http_json(url, method="GET", payload=None, headers=None, timeout=3):
    data = None
    request_headers = {"Accept": "application/json"}
    if headers:
        request_headers.update(headers)
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        request_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=request_headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
        if not raw:
            return {}
        text = raw.decode("utf-8")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw": text}


def syncthing_request(path, method="GET", payload=None):
    config = load_config()
    api_key = syncthing_api_key()
    if not api_key:
        raise RuntimeError("Syncthing API key not found")
    url = config["syncthing_url"].rstrip("/") + path
    return http_json(url, method, payload, {"X-API-Key": api_key}, timeout=5)


def remote_agent_request(path, method="GET", payload=None, timeout=2):
    config = load_config()
    url = "http://{}:{}{}".format(config["remote_ip"], config["remote_agent_port"], path)
    return http_json(
        url,
        method,
        payload,
        {"X-LanSync-Token": config["shared_token"]},
        timeout=timeout,
    )


def local_ip_candidates(config):
    addresses = []
    for value in (config.get("mac_ip"),):
        if value and value not in addresses:
            addresses.append(value)
    try:
        for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            address = item[4][0]
            if not address.startswith("127.") and address not in addresses:
                addresses.append(address)
    except OSError:
        pass
    return addresses


def normalize_device_id(value):
    compact = re.sub(r"[^A-Za-z0-9]", "", str(value or "")).upper()
    if len(compact) == 56:
        return "-".join(compact[index : index + 7] for index in range(0, 56, 7))
    return str(value or "").strip().upper()


def validate_device_id(value):
    device_id = normalize_device_id(value)
    if not re.match(r"^[A-Z0-9]{7}(-[A-Z0-9]{7}){7}$", device_id):
        raise ValueError("Syncthing device ID must contain 8 groups of 7 characters")
    return device_id


def local_idle_seconds():
    system = platform.system()
    try:
        if system == "Darwin":
            output = subprocess.check_output(
                ["ioreg", "-c", "IOHIDSystem"],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=2,
            )
            match = re.search(r'"HIDIdleTime"\s*=\s*(\d+)', output)
            if match:
                return int(match.group(1)) / 1_000_000_000
        elif system == "Windows":
            return 0
    except (subprocess.SubprocessError, OSError, ValueError):
        pass
    return None


def disk_list():
    disks = []
    system = platform.system()
    if system == "Windows":
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            mount = Path(letter + ":\\")
            if mount.exists():
                try:
                    usage = shutil.disk_usage(mount)
                    disks.append(disk_entry(str(mount), str(mount), usage))
                except OSError:
                    continue
        return disks

    try:
        output = subprocess.check_output(["df", "-Pk"], text=True, timeout=3)
    except (subprocess.SubprocessError, OSError):
        return disks
    seen = set()
    for line in output.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 6:
            continue
        mount = " ".join(parts[5:])
        if mount in seen:
            continue
        if mount != "/" and not mount.startswith("/Volumes/"):
            continue
        seen.add(mount)
        try:
            usage = shutil.disk_usage(mount)
        except OSError:
            continue
        disks.append(disk_entry(Path(mount).name or "Macintosh HD", mount, usage))
    return disks


def disk_entry(name, mount, usage):
    return {
        "name": name,
        "mount": mount,
        "total": usage.total,
        "used": usage.used,
        "free": usage.free,
        "percent": round(usage.used / usage.total * 100, 1) if usage.total else 0,
    }


def send_magic_packet(mac_address):
    clean = re.sub(r"[^0-9A-Fa-f]", "", mac_address)
    if len(clean) != 12:
        raise ValueError("Invalid MAC address")
    packet = bytes.fromhex("FF" * 6 + clean * 16)
    destinations = [("<broadcast>", 9), ("255.255.255.255", 9)]
    config = load_config()
    if config.get("remote_ip"):
        octets = config["remote_ip"].split(".")
        if len(octets) == 4:
            destinations.append((".".join(octets[:3] + ["255"]), 9))
    sent = []
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        for target in destinations:
            try:
                sock.sendto(packet, target)
                sent.append(target[0])
            except OSError:
                continue
    if not sent:
        raise RuntimeError("Unable to send Wake-on-LAN packet")
    return sent


def resume_local_sync(folder_id, device_id):
    actions = []
    if folder_id:
        encoded_folder = urllib.parse.quote(folder_id)
        syncthing_request("/rest/system/resume?folder={}".format(encoded_folder), "POST")
        actions.append("folder_resumed")
        syncthing_request("/rest/db/scan?folder={}".format(encoded_folder), "POST")
        actions.append("folder_scan_requested")
    if device_id:
        encoded_device = urllib.parse.quote(device_id)
        syncthing_request("/rest/system/resume?device={}".format(encoded_device), "POST")
        actions.append("device_resumed")
    return actions


def resume_current_sync(payload=None):
    config = load_config()
    folder_id = (payload or {}).get("folder_id") or config["syncthing_folder_id"]
    remote_device_id = (payload or {}).get("device_id") or config["remote_device_id"]
    local_actions = resume_local_sync(folder_id, remote_device_id)
    remote_result = None
    remote_error = ""
    if config.get("remote_ip"):
        try:
            remote_result = remote_agent_request(
                "/api/agent/resume-sync",
                "POST",
                {
                    "folder_id": folder_id,
                    "device_id": config["local_device_id"],
                },
                timeout=10,
            )
        except Exception as exc:
            remote_error = str(exc)
    update_state(
        {
            "last_resume_requested": now_iso(),
            "last_resume_folder_id": folder_id,
            "last_resume_remote_error": remote_error,
        }
    )
    return {
        "ok": True,
        "folder_id": folder_id,
        "local_actions": local_actions,
        "remote": remote_result,
        "remote_error": remote_error,
    }


def classify_sync_health(sync):
    if not sync.get("available"):
        return "unavailable"
    folder_state = str(sync.get("folder_state") or "unknown").lower()
    errors = int(sync.get("errors") or 0)
    need_bytes = int(sync.get("need_bytes") or 0)
    completion = float(sync.get("completion") or 0)
    connected = bool(sync.get("connected"))
    active_states = {
        "scanning",
        "scan-waiting",
        "scan-preparing",
        "syncing",
        "sync-waiting",
        "sync-preparing",
        "cleaning",
    }
    if errors > 0 or folder_state in {"error", "outofsync", "out-of-sync"}:
        return "error"
    if folder_state == "paused":
        return "paused"
    if not connected:
        return "waiting"
    if completion >= 99.995 and need_bytes == 0 and folder_state == "idle":
        return "healthy"
    if folder_state in active_states:
        return "syncing"
    if need_bytes > 0 and folder_state == "idle":
        return "stalled"
    if completion < 100 or need_bytes > 0:
        return "syncing"
    return "healthy"


def syncthing_overview():
    config = load_config()
    result = {
        "available": False,
        "connected": False,
        "completion": 0,
        "need_bytes": 0,
        "address": "",
        "folder_state": "unknown",
        "error": "",
    }
    try:
        connections = syncthing_request("/rest/system/connections")
        conn = connections.get("connections", {}).get(config["remote_device_id"], {})
        completion = syncthing_request(
            "/rest/db/completion?device={}&folder={}".format(
                urllib.parse.quote(config["remote_device_id"]),
                urllib.parse.quote(config["syncthing_folder_id"]),
            )
        )
        status = syncthing_request(
            "/rest/db/status?folder={}".format(urllib.parse.quote(config["syncthing_folder_id"]))
        )
        result.update(
            {
                "available": True,
                "connected": bool(conn.get("connected")),
                "completion": round(float(completion.get("completion", 0)), 2),
                "need_bytes": int(completion.get("needBytes", 0)),
                "address": conn.get("address", ""),
                "is_local": bool(conn.get("isLocal")),
                "client_version": conn.get("clientVersion", ""),
                "folder_state": status.get("state", "unknown"),
                "errors": int(status.get("errors", 0)) + int(status.get("pullErrors", 0)),
                "global_bytes": int(completion.get("globalBytes", 0)),
                "global_items": int(completion.get("globalItems", 0)),
            }
        )
        result["health"] = classify_sync_health(result)
    except Exception as exc:
        result["error"] = str(exc)
        result["health"] = "unavailable"
    return result


def remote_status(sync_status):
    state = load_state()
    agent = None
    agent_error = ""
    try:
        agent = remote_agent_request("/api/agent/status")
        update_state(
            {
                "last_remote_agent": agent,
                "last_remote_seen": now_iso(),
                "last_remote_seen_epoch": time.time(),
            }
        )
    except Exception as exc:
        agent_error = str(exc)

    state = load_state()
    if agent:
        idle_seconds = agent.get("idle_seconds")
        power = agent.get("power_state", "online")
        if power == "online" and isinstance(idle_seconds, (int, float)) and idle_seconds > 900:
            power = "idle"
        return {
            "power_state": power,
            "agent_online": True,
            "agent": agent,
            "last_seen": state.get("last_remote_seen"),
            "detail": "Companion agent connected",
        }

    last_event = state.get("last_remote_event", {})
    if sync_status.get("connected"):
        power = "online"
        detail = "Syncthing connected; companion agent unavailable"
    elif last_event.get("state") == "sleeping":
        power = "sleeping"
        detail = "Last power event reported sleep"
    elif last_event.get("state") in {"shutdown", "shutting_down"}:
        power = "powered_off"
        detail = "Last power event reported a normal shutdown"
    else:
        power = "offline_unknown"
        detail = "Cannot distinguish shutdown, sleep, or network loss without companion heartbeat"
    return {
        "power_state": power,
        "agent_online": False,
        "agent": state.get("last_remote_agent"),
        "last_seen": state.get("last_remote_seen"),
        "detail": detail,
        "agent_error": agent_error,
    }


def overview():
    config = load_config()
    sync_status = syncthing_overview()
    idle = local_idle_seconds()
    return {
        "timestamp": now_iso(),
        "config": public_config(config),
        "local": {
            "name": config["local_name"],
            "hostname": socket.gethostname(),
            "os": platform.platform(),
            "power_state": "idle" if idle is not None and idle > 900 else "online",
            "idle_seconds": idle,
            "disks": disk_list(),
        },
        "remote": remote_status(sync_status),
        "syncthing": sync_status,
        "jobs": job_list(),
    }


def validate_project_paths(source, destination):
    source_path = Path(source).expanduser().resolve()
    dest_path = Path(destination).expanduser().resolve()
    if not source_path.is_dir():
        raise ValueError("Source folder does not exist")
    if source_path == Path("/"):
        raise ValueError("Refusing to process filesystem root")
    if dest_path.exists():
        raise ValueError("Destination already exists")
    if source_path == dest_path or source_path in dest_path.parents:
        raise ValueError("Destination cannot be inside the source folder")
    return source_path, dest_path


def audit_project(payload):
    source = Path(payload.get("source", "")).expanduser().resolve()
    if not source.is_dir():
        raise ValueError("Source folder does not exist")
    proposed = payload.get("destination") or str(source.parent / (source.name + "_cross_platform"))
    destination = Path(proposed).expanduser().resolve()
    if destination.exists():
        destination = Path("/tmp") / ("lan_sync_audit_" + uuid.uuid4().hex)
    planner = Planner(
        source,
        destination,
        DEFAULT_EXCLUDES,
        not bool(payload.get("keep_spaces", False)),
        int(payload.get("max_segment_len", 140)),
    )
    planner.build()
    reason_counts = {}
    for item in planner.renames:
        for reason in item["reasons"]:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
    return {
        "source": str(source),
        "suggested_destination": proposed,
        "total_entries": len(planner.entries),
        "renamed_entries": len(planner.renames),
        "skipped_entries": len(planner.skipped),
        "collisions": len(planner.collisions),
        "reason_counts": reason_counts,
        "examples": [
            {
                "source": item["source_rel"],
                "destination": item["dest_rel"],
                "reasons": item["reasons"],
            }
            for item in planner.renames[:100]
        ],
    }


def job_list():
    with JOBS_LOCK:
        return sorted((dict(value) for value in JOBS.values()), key=lambda item: item["created_at"], reverse=True)


def start_normalize_job(payload):
    source, destination = validate_project_paths(payload.get("source", ""), payload.get("destination", ""))
    job_id = uuid.uuid4().hex[:12]
    job = {
        "id": job_id,
        "type": "normalize",
        "status": "queued",
        "source": str(source),
        "destination": str(destination),
        "created_at": time.time(),
        "progress": 0,
        "copied_files": 0,
        "total_files": 0,
        "message": "Queued",
        "error": "",
    }
    with JOBS_LOCK:
        JOBS[job_id] = job
    thread = threading.Thread(target=run_normalize_job, args=(job_id, payload), daemon=True)
    thread.start()
    return dict(job)


def update_job(job_id, **patch):
    with JOBS_LOCK:
        if job_id in JOBS:
            JOBS[job_id].update(patch)


def run_normalize_job(job_id, payload):
    try:
        source, destination = validate_project_paths(payload["source"], payload["destination"])
        update_job(job_id, status="scanning", message="Scanning names and project files")
        planner = Planner(
            source,
            destination,
            DEFAULT_EXCLUDES,
            not bool(payload.get("keep_spaces", False)),
            int(payload.get("max_segment_len", 140)),
        )
        planner.build()
        total_files = sum(1 for entry in planner.entries if entry["type"] == "file")
        update_job(
            job_id,
            status="copying",
            total_files=total_files,
            renamed_entries=len(planner.renames),
            skipped_entries=len(planner.skipped),
            message="Creating safe copy",
        )

        def progress(index, total, entry):
            update_job(
                job_id,
                copied_files=index,
                total_files=total,
                progress=round(index / total * 100, 1) if total else 100,
                message=entry["dest_rel"],
            )

        copy_tree(planner, progress_callback=progress)
        update_job(job_id, status="verifying", message="Writing reports and verifying copy")
        report_dir = destination / "_CrossPlatformReport"
        write_reports(planner, report_dir, executed=True)
        update_job(
            job_id,
            status="completed",
            progress=100,
            completed_at=time.time(),
            report_dir=str(report_dir),
            message="Safe copy completed",
        )
    except Exception as exc:
        update_job(
            job_id,
            status="failed",
            completed_at=time.time(),
            message="Normalization failed",
            error=str(exc),
        )


def register_local_syncthing_folder(folder_id, label, path):
    config = load_config()
    existing = syncthing_request("/rest/config/folders")
    for folder in existing:
        if folder.get("id") == folder_id:
            raise ValueError("Syncthing folder ID already exists locally")
    default_folder = syncthing_request("/rest/config/defaults/folder")
    default_folder.update(
        {
            "id": folder_id,
            "label": label,
            "path": path,
            "type": "sendreceive",
            "paused": False,
            "devices": [
                {"deviceID": config["local_device_id"], "introducedBy": "", "encryptionPassword": ""},
                {"deviceID": config["remote_device_id"], "introducedBy": "", "encryptionPassword": ""},
            ],
        }
    )
    return syncthing_request("/rest/config/folders", "POST", default_folder)


def ensure_local_folder_id_available(folder_id):
    existing = syncthing_request("/rest/config/folders")
    if any(folder.get("id") == folder_id for folder in existing):
        raise ValueError("Syncthing folder ID already exists locally")


def register_project(payload):
    local_path = Path(payload.get("local_path", "")).expanduser().resolve()
    if not local_path.is_dir():
        raise ValueError("Local project folder does not exist")
    folder_id = re.sub(r"[^a-z0-9-]+", "-", payload.get("folder_id", "").lower()).strip("-")
    if not folder_id:
        raise ValueError("A valid folder ID is required")
    label = payload.get("label") or local_path.name
    remote_path = payload.get("remote_path", "")
    if not remote_path:
        raise ValueError("Remote target path is required")
    ensure_local_folder_id_available(folder_id)
    remote_payload = {
        "folder_id": folder_id,
        "label": label,
        "path": remote_path,
        "remote_device_id": load_config()["local_device_id"],
    }
    remote_result = remote_agent_request("/api/agent/register-folder", "POST", remote_payload, timeout=10)
    local_result = register_local_syncthing_folder(folder_id, label, str(local_path))
    return {"remote": remote_result, "local": local_result, "folder_id": folder_id}


def pairing_info():
    config = load_config()
    folder = {}
    devices = []
    pending_devices = []
    syncthing_error = ""
    try:
        folders = syncthing_request("/rest/config/folders")
        folder = next((item for item in folders if item.get("id") == config["syncthing_folder_id"]), {})
        devices = syncthing_request("/rest/config/devices")
        try:
            pending_raw = syncthing_request("/rest/cluster/pending/devices")
            if isinstance(pending_raw, dict):
                for device_id, item in pending_raw.items():
                    pending_devices.append(
                        {
                            "device_id": device_id,
                            "name": item.get("name", ""),
                            "addresses": item.get("addresses", []),
                        }
                    )
        except Exception:
            pending_devices = []
    except Exception as exc:
        syncthing_error = str(exc)

    dashboard_urls = ["http://127.0.0.1:{}".format(config["listen_port"])]
    dashboard_urls.extend(
        "http://{}:{}".format(address, config["listen_port"])
        for address in local_ip_candidates(config)
    )
    dashboard_urls = list(dict.fromkeys(dashboard_urls))
    windows_tool_path = str(Path(config["sync_root"]) / "_tools" / "LanSyncDashboardWindows")
    return {
        "controller": {
            "name": config["local_name"],
            "dashboard_urls": dashboard_urls,
            "syncthing_url": config["syncthing_url"],
            "device_id": config["local_device_id"],
            "mac_address": config["mac_mac"],
        },
        "folder": {
            "id": config["syncthing_folder_id"],
            "label": folder.get("label") or config["syncthing_folder_id"],
            "path": folder.get("path") or config["sync_root"],
            "shared_with": [item.get("deviceID", "") for item in folder.get("devices", [])],
        },
        "known_devices": [
            {
                "device_id": item.get("deviceID", ""),
                "name": item.get("name", ""),
                "addresses": item.get("addresses", []),
            }
            for item in devices
        ],
        "pending_devices": pending_devices,
        "companion": {
            "windows_package_path": windows_tool_path,
            "windows_agent_port": config["remote_agent_port"],
            "remote_project_base": config["remote_project_base"],
        },
        "syncthing_error": syncthing_error,
    }


def add_syncthing_device(payload):
    config = load_config()
    device_id = validate_device_id(payload.get("device_id"))
    if device_id == config["local_device_id"]:
        raise ValueError("Cannot add this Mac as a remote device")
    name = str(payload.get("name") or "New LAN Device").strip()[:80]
    raw_address = str(payload.get("address") or "dynamic").strip()
    addresses = [raw_address] if raw_address else ["dynamic"]
    folder_id = str(payload.get("folder_id") or config["syncthing_folder_id"]).strip()

    syncthing_config = syncthing_request("/rest/config")
    device_added = False
    device_updated = False
    devices = syncthing_config.setdefault("devices", [])
    existing = next((item for item in devices if item.get("deviceID") == device_id), None)
    if existing:
        if name:
            existing["name"] = name
        if addresses:
            existing["addresses"] = addresses
        device_updated = True
    else:
        try:
            new_device = syncthing_request("/rest/config/defaults/device")
        except Exception:
            new_device = {}
        new_device.update(
            {
                "deviceID": device_id,
                "name": name,
                "addresses": addresses,
                "paused": False,
                "introducer": False,
                "autoAcceptFolders": False,
            }
        )
        devices.append(new_device)
        device_added = True

    folder_shared = False
    folders = syncthing_config.setdefault("folders", [])
    folder = next((item for item in folders if item.get("id") == folder_id), None)
    if not folder:
        raise ValueError("Syncthing folder ID not found locally: {}".format(folder_id))
    folder_devices = folder.setdefault("devices", [])
    if not any(item.get("deviceID") == device_id for item in folder_devices):
        folder_devices.append({"deviceID": device_id, "introducedBy": "", "encryptionPassword": ""})
        folder_shared = True

    syncthing_request("/rest/config", "PUT", syncthing_config)
    return {
        "ok": True,
        "device_id": device_id,
        "name": name,
        "addresses": addresses,
        "folder_id": folder_id,
        "device_added": device_added,
        "device_updated": device_updated,
        "folder_shared": folder_shared,
    }


def version_key(value):
    parts = [int(part) for part in re.findall(r"\d+", str(value or ""))]
    return tuple(parts or [0])


def github_api(path):
    return http_json(
        "https://api.github.com{}".format(path),
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "Red-LAN-Sync-Dashboard/{}".format(APP_VERSION),
        },
        timeout=6,
    )


def check_github_update():
    config = load_config()
    repo = str(config.get("github_repo") or "").strip()
    current_version = str(config.get("current_version") or APP_VERSION)
    if not repo:
        return {
            "configured": False,
            "current_version": current_version,
            "has_update": False,
            "message": "GitHub repository is not configured",
        }

    result = {
        "configured": True,
        "repo": repo,
        "current_version": current_version,
        "has_update": False,
        "latest_version": "",
        "latest_name": "",
        "preview": "",
        "url": "https://github.com/{}".format(repo),
        "published_at": "",
        "mode": "release",
    }
    try:
        latest = github_api("/repos/{}/releases/latest".format(repo))
        tag = str(latest.get("tag_name") or latest.get("name") or "")
        latest_version = tag.lstrip("vV") or tag
        result.update(
            {
                "latest_version": latest_version,
                "latest_name": latest.get("name") or tag,
                "preview": str(latest.get("body") or "").strip()[:700],
                "url": latest.get("html_url") or result["url"],
                "published_at": latest.get("published_at") or "",
                "has_update": bool(latest_version) and version_key(latest_version) > version_key(current_version),
            }
        )
        return result
    except Exception as release_exc:
        result["mode"] = "commit"
        result["release_error"] = str(release_exc)

    try:
        repo_info = github_api("/repos/{}".format(repo))
        branch = repo_info.get("default_branch") or "main"
        commit = github_api("/repos/{}/commits/{}".format(repo, urllib.parse.quote(branch)))
        info = commit.get("commit", {})
        message = str(info.get("message") or "").splitlines()[0]
        sha = str(commit.get("sha") or "")
        result.update(
            {
                "latest_version": sha[:7],
                "latest_name": message or "Latest commit",
                "preview": message,
                "url": commit.get("html_url") or result["url"],
                "published_at": info.get("committer", {}).get("date") or "",
                "has_update": False,
            }
        )
    except Exception as exc:
        result.update({"error": str(exc), "has_update": False})
    return result


class Handler(BaseHTTPRequestHandler):
    server_version = "LanSyncDashboard/1.0"

    def log_message(self, fmt, *args):
        print("{} - {}".format(self.address_string(), fmt % args), flush=True)

    def client_is_local(self):
        return self.client_address[0] in {"127.0.0.1", "::1"}

    def token_valid(self):
        return secrets.compare_digest(
            self.headers.get("X-LanSync-Token", ""),
            load_config()["shared_token"],
        )

    def require_action_access(self):
        if self.client_is_local() or self.token_valid():
            return True
        self.send_json({"error": "Action requires localhost or companion token"}, status=403)
        return False

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > 1_000_000:
            raise ValueError("Request too large")
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8"))

    def send_json(self, value, status=200):
        data = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        try:
            if path == "/api/overview":
                return self.send_json(overview())
            if path == "/api/config":
                return self.send_json(public_config(load_config()))
            if path == "/api/pairing":
                return self.send_json(pairing_info())
            if path == "/api/update/check":
                return self.send_json(check_github_update())
            if path == "/api/jobs":
                return self.send_json({"jobs": job_list()})
            if path == "/api/disks":
                remote = None
                remote_error = ""
                try:
                    remote = remote_agent_request("/api/agent/status")
                except Exception as exc:
                    remote_error = str(exc)
                return self.send_json(
                    {
                        "local": disk_list(),
                        "remote": remote.get("disks", []) if remote else [],
                        "remote_project_base": remote.get("project_base", "") if remote else load_config()["remote_project_base"],
                        "remote_error": remote_error,
                    }
                )
            if path.startswith("/api/jobs/"):
                job_id = path.rsplit("/", 1)[-1]
                with JOBS_LOCK:
                    job = JOBS.get(job_id)
                if not job:
                    return self.send_json({"error": "Job not found"}, 404)
                return self.send_json(job)
            return self.serve_static(path)
        except Exception as exc:
            return self.send_json({"error": str(exc)}, 500)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        try:
            payload = self.read_json()
            if path == "/api/agent/event":
                if not self.token_valid():
                    return self.send_json({"error": "Invalid companion token"}, 403)
                event = {
                    "state": payload.get("state", "unknown"),
                    "hostname": payload.get("hostname", ""),
                    "timestamp": payload.get("timestamp", now_iso()),
                    "received_at": now_iso(),
                }
                update_state(
                    {
                        "last_remote_event": event,
                        "last_remote_seen": event["received_at"],
                        "last_remote_seen_epoch": time.time(),
                    }
                )
                return self.send_json({"ok": True})

            if not self.require_action_access():
                return
            if path == "/api/config":
                return self.send_json({"config": public_config(update_config(payload))})
            if path == "/api/audit":
                return self.send_json(audit_project(payload))
            if path == "/api/normalize":
                return self.send_json({"job": start_normalize_job(payload)}, 202)
            if path == "/api/wake":
                mac = payload.get("mac") or load_config()["remote_mac"]
                return self.send_json({"ok": True, "sent_to": send_magic_packet(mac)})
            if path == "/api/sync/resume":
                return self.send_json(resume_current_sync(payload))
            if path == "/api/remote/target":
                target = payload.get("path", "")
                if not target:
                    raise ValueError("Target path is required")
                result = remote_agent_request("/api/agent/target", "POST", {"path": target}, timeout=10)
                update_config({"remote_project_base": target})
                return self.send_json({"ok": True, "remote": result})
            if path == "/api/devices/add":
                return self.send_json(add_syncthing_device(payload))
            if path == "/api/projects/register":
                return self.send_json(register_project(payload))
            return self.send_json({"error": "Not found"}, 404)
        except ValueError as exc:
            return self.send_json({"error": str(exc)}, 400)
        except urllib.error.URLError as exc:
            return self.send_json({"error": "Remote companion unavailable: {}".format(exc)}, 502)
        except Exception as exc:
            return self.send_json({"error": str(exc)}, 500)

    def serve_static(self, request_path):
        relative = "index.html" if request_path in {"", "/"} else request_path.lstrip("/")
        candidate = (STATIC_DIR / relative).resolve()
        if STATIC_DIR.resolve() not in candidate.parents and candidate != STATIC_DIR.resolve():
            return self.send_json({"error": "Invalid path"}, 400)
        if not candidate.is_file():
            candidate = STATIC_DIR / "index.html"
        data = candidate.read_bytes()
        mime, _ = mimetypes.guess_type(candidate.name)
        self.send_response(200)
        self.send_header("Content-Type", (mime or "application/octet-stream") + ("; charset=utf-8" if (mime or "").startswith("text/") else ""))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    parser = argparse.ArgumentParser(description="LAN Sync companion dashboard")
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    args = parser.parse_args()
    config = load_config()
    host = args.host or config["listen_host"]
    port = args.port or int(config["listen_port"])
    server = ThreadingHTTPServer((host, port), Handler)
    print("LAN Sync Dashboard: http://127.0.0.1:{}".format(port), flush=True)
    print("LAN address: http://{}:{}".format(config["mac_ip"], port), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
