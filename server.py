#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import http.cookies
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
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from dependency_auditor import audit_project_dependencies, endpoint_inventory
from project_packager import DEFAULT_EXCLUDES, Planner, copy_tree, write_reports


APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
RUNTIME_ASSET_DIR = APP_DIR / "runtime-assets"
CUSTOM_ICON_META_PATH = RUNTIME_ASSET_DIR / "app-icon.json"
CONFIG_PATH = APP_DIR / "config.json"
STATE_PATH = APP_DIR / "runtime-state.json"
APP_DISPLAY_NAME = "SystemSync"
APP_VERSION = "0.1.6"
ICON_UPLOAD_TYPES = {
    "image/png": ("png", b"\x89PNG\r\n\x1a\n"),
    "image/jpeg": ("jpg", b"\xff\xd8"),
}

DEFAULT_CONFIG = {
    "listen_host": "0.0.0.0",
    "listen_port": 8765,
    "dashboard_alias": "system-sync.local",
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
    "github_repo": "RedHong01/SystemSync",
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
            "dashboard_alias",
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


def dashboard_alias(config):
    value = str(config.get("dashboard_alias") or "").strip().lower()
    value = re.sub(r"^https?://", "", value).split("/", 1)[0].split(":", 1)[0]
    if not value or value == "localhost" or value.startswith("127."):
        return ""
    if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{0,251}[a-z0-9]", value):
        return ""
    return value


def dashboard_urls(config):
    urls = ["http://127.0.0.1:{}".format(config["listen_port"])]
    urls.extend(
        "http://{}:{}".format(address, config["listen_port"])
        for address in local_ip_candidates(config)
    )
    alias = dashboard_alias(config)
    if alias:
        urls.append("http://{}:{}".format(alias, config["listen_port"]))
    return list(dict.fromkeys(urls))


def public_config(config):
    value = {key: item for key, item in config.items() if key != "shared_token"}
    value["current_version"] = APP_VERSION
    value["dashboard_urls"] = dashboard_urls(config)
    value["icon"] = current_icon_info()
    return value


def load_custom_icon_meta():
    try:
        return json.loads(CUSTOM_ICON_META_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def current_icon_info():
    meta = load_custom_icon_meta()
    filename = meta.get("filename", "")
    if filename:
        candidate = (RUNTIME_ASSET_DIR / filename).resolve()
        try:
            if RUNTIME_ASSET_DIR.resolve() in candidate.parents and candidate.is_file():
                return {
                    "path": "/runtime-icon/{}?v={}".format(filename, int(candidate.stat().st_mtime)),
                    "custom": True,
                    "mime": meta.get("mime", mimetypes.guess_type(filename)[0] or "application/octet-stream"),
                    "name": meta.get("name", filename),
                    "updated_at": meta.get("updated_at", ""),
                }
        except OSError:
            pass
    return {
        "path": "/app-icon.svg",
        "custom": False,
        "mime": "image/svg+xml",
        "name": APP_DISPLAY_NAME,
        "updated_at": "",
    }


def upload_custom_icon(payload):
    data_url = str(payload.get("data_url") or "")
    if "," not in data_url or ";base64" not in data_url.split(",", 1)[0]:
        raise ValueError("Icon upload must be a base64 data URL")
    header, encoded = data_url.split(",", 1)
    mime = header.removeprefix("data:").split(";", 1)[0].lower()
    if mime not in ICON_UPLOAD_TYPES:
        raise ValueError("Icon must be a PNG or JPG image")
    extension, signature = ICON_UPLOAD_TYPES[mime]
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Icon data is not valid base64") from exc
    if len(raw) > 3 * 1024 * 1024:
        raise ValueError("Icon file is too large; keep it under 3 MB")
    if not raw.startswith(signature):
        raise ValueError("Icon file content does not match its image type")

    RUNTIME_ASSET_DIR.mkdir(parents=True, exist_ok=True)
    for existing in RUNTIME_ASSET_DIR.glob("app-icon.*"):
        if existing.name != "app-icon.json":
            existing.unlink(missing_ok=True)
    filename = "app-icon.{}".format(extension)
    (RUNTIME_ASSET_DIR / filename).write_bytes(raw)
    save_json(
        CUSTOM_ICON_META_PATH,
        {
            "filename": filename,
            "mime": mime,
            "name": str(payload.get("name") or filename),
            "bytes": len(raw),
            "updated_at": now_iso(),
        },
    )
    return {"ok": True, "icon": current_icon_info()}


def reset_custom_icon():
    for existing in RUNTIME_ASSET_DIR.glob("app-icon.*"):
        existing.unlink(missing_ok=True)
    return {"ok": True, "icon": current_icon_info()}


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


def build_project_planner(payload):
    source = Path(payload.get("source", "")).expanduser().resolve()
    if not source.is_dir():
        raise ValueError("Source folder does not exist")
    if source.anchor and source == Path(source.anchor):
        raise ValueError("Refusing to process filesystem root")
    proposed = payload.get("destination") or str(source.parent / (source.name + "_cross_platform"))
    destination = Path(proposed).expanduser().resolve()
    if destination.exists():
        destination = Path(tempfile.gettempdir()) / ("lan_sync_audit_" + uuid.uuid4().hex)
    planner = Planner(
        source,
        destination,
        DEFAULT_EXCLUDES,
        not bool(payload.get("keep_spaces", False)),
        int(payload.get("max_segment_len", 140)),
    )
    planner.build()
    return planner, proposed


def audit_project(payload):
    planner, proposed = build_project_planner(payload)
    reason_counts = {}
    for item in planner.renames:
        for reason in item["reasons"]:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
    return {
        "source": str(planner.source),
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


def rel_parent(value):
    return value.rsplit("/", 1)[0] if "/" in value else ""


def rel_name(value):
    return value.rsplit("/", 1)[-1]


def relative_path_from_posix(value):
    if not value:
        return Path()
    return Path(*[part for part in value.split("/") if part])


def fs_key(path):
    return os.path.normcase(os.path.abspath(str(path)))


def source_rename_operations(planner):
    operations = []
    for item in planner.renames:
        parent_dest = rel_parent(item["dest_rel"])
        operations.append(
            {
                "type": item["type"],
                "source_rel": item["source_rel"],
                "dest_rel": item["dest_rel"],
                "parent_dest": parent_dest,
                "source_name": rel_name(item["source_rel"]),
                "target_name": rel_name(item["dest_rel"]),
                "reasons": item["reasons"],
            }
        )
    return operations


def source_rename_plan_hash(planner, operations):
    material = {
        "source": str(planner.source),
        "replace_spaces": planner.replace_spaces,
        "max_segment_len": planner.max_segment_len,
        "operations": operations,
    }
    encoded = json.dumps(material, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def source_rename_preview(payload):
    planner, _proposed = build_project_planner(payload)
    operations = source_rename_operations(planner)
    try:
        preview_limit = int(payload.get("limit", 500))
    except (TypeError, ValueError):
        preview_limit = 500
    preview_limit = max(1, min(2000, preview_limit))
    return {
        "source": str(planner.source),
        "plan_hash": source_rename_plan_hash(planner, operations),
        "operation_count": len(operations),
        "collision_count": len(planner.collisions),
        "truncated": len(operations) > preview_limit,
        "preview_limit": preview_limit,
        "operations": operations[:preview_limit],
    }


def apply_source_rename_operations(source, operations):
    grouped = {}
    for operation in operations:
        grouped.setdefault(operation["parent_dest"], []).append(operation)

    applied = []
    for parent in sorted(grouped, key=lambda value: len(value.split("/")) if value else 0):
        parent_dir = source / relative_path_from_posix(parent)
        if not parent_dir.is_dir():
            raise ValueError("Planned parent folder is missing: {}".format(parent or "."))

        prepared = []
        planned_sources = set()
        for operation in grouped[parent]:
            source_path = parent_dir / operation["source_name"]
            target_path = parent_dir / operation["target_name"]
            if fs_key(source_path) == fs_key(target_path):
                continue
            if not source_path.exists():
                raise ValueError("Planned source path is missing; preview again: {}".format(operation["source_rel"]))
            planned_sources.add(fs_key(source_path))
            prepared.append((operation, source_path, target_path))

        for operation, _source_path, target_path in prepared:
            if target_path.exists() and fs_key(target_path) not in planned_sources:
                raise ValueError("Target path already exists; cannot rename safely: {}".format(operation["dest_rel"]))

        staged = []
        try:
            for index, (operation, source_path, target_path) in enumerate(prepared, start=1):
                temp_path = parent_dir / ".lan-sync-rename-{}-{}".format(uuid.uuid4().hex, index)
                while temp_path.exists():
                    temp_path = parent_dir / ".lan-sync-rename-{}-{}".format(uuid.uuid4().hex, index)
                source_path.rename(temp_path)
                staged.append((operation, temp_path, source_path, target_path))

            for operation, temp_path, source_path, target_path in staged:
                if target_path.exists():
                    raise ValueError("Target path appeared during rename: {}".format(operation["dest_rel"]))
                temp_path.rename(target_path)
                applied.append(
                    {
                        "type": operation["type"],
                        "source_rel": operation["source_rel"],
                        "dest_rel": operation["dest_rel"],
                        "source_abs": str(source_path),
                        "dest_abs": str(target_path),
                        "reasons": operation["reasons"],
                    }
                )
        except Exception:
            for _operation, temp_path, source_path, _target_path in reversed(staged):
                if temp_path.exists() and not source_path.exists():
                    temp_path.rename(source_path)
            raise

    return applied


def apply_source_renames(payload):
    if not payload.get("confirm"):
        raise ValueError("Source rename confirmation is required")
    planner, _proposed = build_project_planner(payload)
    operations = source_rename_operations(planner)
    expected_hash = source_rename_plan_hash(planner, operations)
    if payload.get("plan_hash") != expected_hash:
        raise ValueError("Rename plan changed; preview again before applying")
    applied = apply_source_rename_operations(planner.source, operations) if operations else []
    verify_planner, _verify_proposed = build_project_planner(payload)
    remaining = len(source_rename_operations(verify_planner))
    return {
        "ok": True,
        "source": str(planner.source),
        "plan_hash": expected_hash,
        "applied_count": len(applied),
        "remaining_count": remaining,
        "operations": applied[:500],
        "truncated": len(applied) > 500,
    }


def dependency_audit(payload):
    source = Path(payload.get("source", "")).expanduser().resolve()
    remote_inventory = None
    remote_error = ""
    if payload.get("compare_remote", True):
        try:
            remote_inventory = remote_agent_request("/api/agent/dependencies", timeout=25)
        except Exception as exc:
            remote_error = str(exc)
    bundle_dir = None
    if payload.get("bundle_dir"):
        bundle_dir = Path(payload["bundle_dir"]).expanduser().resolve()
    result = audit_project_dependencies(
        source,
        package=bool(payload.get("package", False)),
        bundle_dir=bundle_dir,
        remote_inventory=remote_inventory,
    )
    result["remote_error"] = remote_error
    return result


NORMALIZATION_REPORT_DIR = "_CrossPlatformReport"
REPORT_SCAN_EXCLUDES = {
    ".git",
    ".stfolder",
    ".stversions",
    "node_modules",
    "Library",
    "__pycache__",
    "_DependencyBundle",
}


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def report_timestamp(path):
    try:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(path.stat().st_mtime))
    except OSError:
        return ""


def is_normalization_report_dir(path):
    return path.name == NORMALIZATION_REPORT_DIR and (path / "summary.json").is_file()


def read_report_json(report_dir, filename, default):
    path = report_dir / filename
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default.copy() if hasattr(default, "copy") else default


def project_file_counts(summary):
    files = summary.get("project_files") if isinstance(summary, dict) else {}
    if not isinstance(files, dict):
        return {}
    return {key: len(value) for key, value in files.items() if isinstance(value, list) and value}


def normalization_report_summary(report_dir):
    report_dir = Path(report_dir).expanduser().resolve()
    if not is_normalization_report_dir(report_dir):
        raise ValueError("Not a normalization report directory: {}".format(report_dir))
    summary = read_report_json(report_dir, "summary.json", {})
    rename_map = read_report_json(report_dir, "rename_map.json", [])
    collisions = read_report_json(report_dir, "collisions.json", [])
    skipped = read_report_json(report_dir, "skipped.json", [])
    destination = str(summary.get("destination") or report_dir.parent)
    source = str(summary.get("source") or "")
    renamed = safe_int(summary.get("renamed_entries"), len(rename_map) if isinstance(rename_map, list) else 0)
    collision_count = safe_int(summary.get("collision_resolutions"), len(collisions) if isinstance(collisions, list) else 0)
    skipped_count = safe_int(summary.get("skipped_entries"), len(skipped) if isinstance(skipped, list) else 0)
    warnings = summary.get("warnings") if isinstance(summary.get("warnings"), list) else []
    post_copy_risks = summary.get("post_copy_risks") if isinstance(summary.get("post_copy_risks"), list) else []
    unity_meta_issues = summary.get("unity_meta_pair_issues") if isinstance(summary.get("unity_meta_pair_issues"), list) else []
    return {
        "report_dir": str(report_dir),
        "display_name": Path(destination).name or report_dir.parent.name,
        "source": source,
        "destination": destination,
        "executed": bool(summary.get("executed", True)),
        "generated_at": str(summary.get("generated_at") or ""),
        "updated_at": report_timestamp(report_dir),
        "total_entries": safe_int(summary.get("total_entries")),
        "renamed_entries": renamed,
        "skipped_entries": skipped_count,
        "collision_resolutions": collision_count,
        "warning_count": len(warnings),
        "post_copy_risk_count": len(post_copy_risks),
        "unity_meta_issue_count": len(unity_meta_issues),
        "project_file_counts": project_file_counts(summary),
        "paths": {
            "summary": str(report_dir / "summary.json"),
            "rename_map": str(report_dir / "rename_map.json"),
            "collisions": str(report_dir / "collisions.json"),
            "skipped": str(report_dir / "skipped.json"),
        },
    }


def report_candidates_from_path(value):
    if not value:
        return []
    try:
        candidate = Path(value).expanduser().resolve()
    except (OSError, RuntimeError, ValueError):
        return []
    if candidate.name == NORMALIZATION_REPORT_DIR:
        return [candidate]
    return [candidate / NORMALIZATION_REPORT_DIR]


def iter_normalization_report_dirs(root, max_reports=120):
    try:
        root = Path(root).expanduser().resolve()
    except (OSError, RuntimeError, ValueError):
        return
    if not root.is_dir():
        return
    found = 0
    for current, dirs, files in os.walk(root):
        current_path = Path(current)
        if current_path.name == NORMALIZATION_REPORT_DIR and "summary.json" in files:
            yield current_path
            found += 1
            dirs[:] = []
            if found >= max_reports:
                return
            continue
        dirs[:] = [name for name in dirs if name not in REPORT_SCAN_EXCLUDES and not name.startswith(".")]


def list_normalization_reports(root_value="", candidates=None):
    config = load_config()
    roots = []
    if root_value:
        roots.append(root_value)
    if config.get("sync_root"):
        roots.append(config["sync_root"])

    report_dirs = []
    with JOBS_LOCK:
        for job in JOBS.values():
            if job.get("report_dir"):
                report_dirs.extend(report_candidates_from_path(job.get("report_dir")))
            elif job.get("destination"):
                report_dirs.extend(report_candidates_from_path(job.get("destination")))
    for candidate in candidates or []:
        report_dirs.extend(report_candidates_from_path(candidate))
    for root in roots:
        report_dirs.extend(iter_normalization_report_dirs(root) or [])

    seen = set()
    reports = []
    errors = []
    for report_dir in report_dirs:
        try:
            resolved = Path(report_dir).expanduser().resolve()
            key = os.path.normcase(str(resolved))
            if key in seen or not is_normalization_report_dir(resolved):
                continue
            seen.add(key)
            reports.append(normalization_report_summary(resolved))
        except Exception as exc:
            errors.append(str(exc))
    reports.sort(key=lambda item: item.get("updated_at") or item.get("generated_at") or "", reverse=True)
    return {"reports": reports, "count": len(reports), "errors": errors[:10], "scan_roots": list(dict.fromkeys(str(item) for item in roots if item))}


def normalization_report_detail(report_dir_value, limit=500):
    report_dir = Path(report_dir_value).expanduser().resolve()
    summary = normalization_report_summary(report_dir)
    limit = max(1, min(safe_int(limit, 500), 5000))
    rename_map = read_report_json(report_dir, "rename_map.json", [])
    collisions = read_report_json(report_dir, "collisions.json", [])
    skipped = read_report_json(report_dir, "skipped.json", [])
    raw_summary = read_report_json(report_dir, "summary.json", {})
    warnings = raw_summary.get("warnings") if isinstance(raw_summary.get("warnings"), list) else []
    post_copy_risks = raw_summary.get("post_copy_risks") if isinstance(raw_summary.get("post_copy_risks"), list) else []
    unity_meta_issues = raw_summary.get("unity_meta_pair_issues") if isinstance(raw_summary.get("unity_meta_pair_issues"), list) else []
    if not isinstance(rename_map, list):
        rename_map = []
    if not isinstance(collisions, list):
        collisions = []
    if not isinstance(skipped, list):
        skipped = []
    summary.update(
        {
            "rename_map": rename_map[:limit],
            "rename_map_total": len(rename_map),
            "rename_map_truncated": len(rename_map) > limit,
            "collisions": collisions[:limit],
            "skipped": skipped[:limit],
            "warnings": warnings[:limit],
            "post_copy_risks": post_copy_risks[:limit],
            "unity_meta_pair_issues": unity_meta_issues[:limit],
        }
    )
    return summary


def reveal_normalization_path(payload):
    if platform.system() != "Darwin":
        return {"ok": False, "supported": False, "message": "Reveal is only supported on macOS controller hosts"}
    report_dir = Path(payload.get("report_dir", "")).expanduser().resolve()
    detail = normalization_report_detail(str(report_dir), limit=1)
    target_name = str(payload.get("target") or "destination")
    targets = {
        "report": report_dir,
        "destination": Path(detail["destination"]),
        "source": Path(detail["source"]) if detail.get("source") else report_dir,
    }
    target = targets.get(target_name, targets["destination"])
    if not target.exists():
        target = report_dir
    subprocess.run(["/usr/bin/open", str(target)], check=False, timeout=10)
    return {"ok": True, "supported": True, "target": str(target)}


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


def normalized_compare_path(value):
    try:
        return os.path.normcase(os.path.abspath(os.path.expanduser(str(value or ""))))
    except (OSError, TypeError, ValueError):
        return str(value or "").strip()


def folder_path_matches(existing_path, expected_path):
    return normalized_compare_path(existing_path) == normalized_compare_path(expected_path)


def ensure_local_folder_conflict_free(folder_id, path):
    existing = syncthing_request("/rest/config/folders")
    for folder in existing:
        if folder.get("id") != folder_id:
            continue
        if not folder_path_matches(folder.get("path", ""), path):
            raise ValueError(
                "Syncthing folder ID already exists locally with a different path: {}".format(folder.get("path", ""))
            )
        return folder
    return None


def register_local_syncthing_folder(folder_id, label, path):
    config = load_config()
    existing_folder = ensure_local_folder_conflict_free(folder_id, path)
    if existing_folder:
        return {"ok": True, "existing": True, "folder_id": folder_id, "path": existing_folder.get("path", path)}

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
    syncthing_request("/rest/config/folders", "POST", default_folder)
    return {"ok": True, "existing": False, "folder_id": folder_id, "path": path}


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
    ensure_local_folder_conflict_free(folder_id, str(local_path))
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

    urls = dashboard_urls(config)
    windows_tool_path = str(Path(config["sync_root"]) / "_tools" / "SystemSyncWindows")
    dock_app_path = str(Path.home() / "Applications" / "SystemSync.app")
    icon = current_icon_info()
    return {
        "controller": {
            "name": config["local_name"],
            "dashboard_urls": urls,
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
        "dock": {
            "supported": platform.system() == "Darwin",
            "app_path": dock_app_path,
            "icon_path": icon["path"],
            "installed": Path(dock_app_path).exists(),
        },
        "icon": icon,
        "syncthing_error": syncthing_error,
    }


def install_dock_shortcut():
    if platform.system() != "Darwin":
        return {"ok": False, "supported": False, "message": "Dock shortcuts are only supported on macOS"}
    script = APP_DIR / "mac" / "install-dock-shortcut.sh"
    if not script.is_file():
        raise FileNotFoundError("Dock installer not found: {}".format(script))
    result = subprocess.run(
        ["/bin/zsh", str(script)],
        cwd=str(APP_DIR),
        text=True,
        capture_output=True,
        timeout=90,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "Dock installer failed").strip())
    app_path = str(Path.home() / "Applications" / "SystemSync.app")
    return {"ok": True, "supported": True, "app_path": app_path, "output": result.stdout.strip()}


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
            "User-Agent": "SystemSync/{}".format(APP_VERSION),
        },
        timeout=6,
    )


def check_github_update():
    config = load_config()
    repo = str(config.get("github_repo") or "").strip()
    current_version = APP_VERSION
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
    server_version = "SystemSync/1.0"

    def log_message(self, fmt, *args):
        print("{} - {}".format(self.address_string(), fmt % args), flush=True)

    def client_is_local(self):
        return self.client_address[0] in {"127.0.0.1", "::1"}

    def token_valid(self):
        config = load_config()
        cookie = http.cookies.SimpleCookie(self.headers.get("Cookie", ""))
        cookie_token = ""
        if "LanSyncToken" in cookie:
            cookie_token = cookie["LanSyncToken"].value
        return secrets.compare_digest(
            self.headers.get("X-LanSync-Token", ""),
            config["shared_token"],
        ) or secrets.compare_digest(cookie_token, config["shared_token"])

    def require_action_access(self):
        if self.client_is_local() or self.token_valid():
            return True
        self.send_json({"error": "Action requires localhost, companion token, or launcher-authenticated browser session"}, status=403)
        return False

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > 6_000_000:
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

    def send_redirect(self, location, status=302, headers=None):
        data = b""
        self.send_response(status)
        self.send_header("Location", location)
        self.send_header("Cache-Control", "no-store")
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        try:
            if path == "/auth":
                query = urllib.parse.parse_qs(parsed.query)
                token = (query.get("token") or [""])[0]
                if not secrets.compare_digest(token, load_config()["shared_token"]):
                    return self.send_json({"error": "Invalid dashboard token"}, 403)
                cookie = http.cookies.SimpleCookie()
                cookie["LanSyncToken"] = token
                cookie["LanSyncToken"]["path"] = "/"
                cookie["LanSyncToken"]["max-age"] = 60 * 60 * 24 * 14
                cookie["LanSyncToken"]["httponly"] = True
                cookie["LanSyncToken"]["samesite"] = "Lax"
                return self.send_redirect("/", headers={"Set-Cookie": cookie.output(header="").strip()})
            if path == "/api/overview":
                return self.send_json(overview())
            if path == "/api/config":
                return self.send_json(public_config(load_config()))
            if path == "/api/pairing":
                return self.send_json(pairing_info())
            if path == "/api/update/check":
                return self.send_json(check_github_update())
            if path == "/api/normalizations":
                query = urllib.parse.parse_qs(parsed.query)
                return self.send_json(list_normalization_reports((query.get("root") or [""])[0], query.get("candidate") or []))
            if path == "/api/normalizations/report":
                query = urllib.parse.parse_qs(parsed.query)
                return self.send_json(normalization_report_detail((query.get("path") or [""])[0], (query.get("limit") or [500])[0]))
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
            if path == "/api/dependencies/local":
                return self.send_json(endpoint_inventory())
            if path == "/api/dependencies/remote":
                return self.send_json(remote_agent_request("/api/agent/dependencies", timeout=25))
            if path.startswith("/api/jobs/"):
                job_id = path.rsplit("/", 1)[-1]
                with JOBS_LOCK:
                    job = JOBS.get(job_id)
                if not job:
                    return self.send_json({"error": "Job not found"}, 404)
                return self.send_json(job)
            if path.startswith("/runtime-icon/"):
                return self.serve_runtime_icon(path)
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
            if path == "/api/source-renames/preview":
                return self.send_json(source_rename_preview(payload))
            if path == "/api/source-renames/apply":
                return self.send_json(apply_source_renames(payload))
            if path == "/api/dependencies/audit":
                return self.send_json(dependency_audit(payload))
            if path == "/api/normalizations/reveal":
                return self.send_json(reveal_normalization_path(payload))
            if path == "/api/wake":
                mac = payload.get("mac") or load_config()["remote_mac"]
                return self.send_json({"ok": True, "sent_to": send_magic_packet(mac)})
            if path == "/api/sync/resume":
                return self.send_json(resume_current_sync(payload))
            if path == "/api/dock/install":
                return self.send_json(install_dock_shortcut())
            if path == "/api/icon/upload":
                return self.send_json(upload_custom_icon(payload))
            if path == "/api/icon/reset":
                return self.send_json(reset_custom_icon())
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

    def serve_runtime_icon(self, request_path):
        filename = urllib.parse.unquote(request_path.rsplit("/", 1)[-1])
        if not re.fullmatch(r"app-icon\.(png|jpg|jpeg)", filename):
            return self.send_json({"error": "Icon not found"}, 404)
        candidate = (RUNTIME_ASSET_DIR / filename).resolve()
        if RUNTIME_ASSET_DIR.resolve() not in candidate.parents or not candidate.is_file():
            return self.send_json({"error": "Icon not found"}, 404)
        data = candidate.read_bytes()
        mime, _ = mimetypes.guess_type(candidate.name)
        self.send_response(200)
        self.send_header("Content-Type", mime or "application/octet-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    parser = argparse.ArgumentParser(description="SystemSync companion dashboard")
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    args = parser.parse_args()
    config = load_config()
    host = args.host or config["listen_host"]
    port = args.port or int(config["listen_port"])
    server = ThreadingHTTPServer((host, port), Handler)
    print("SystemSync: http://127.0.0.1:{}".format(port), flush=True)
    alias = dashboard_alias(config)
    if alias:
        print("Friendly alias: http://{}:{}".format(alias, port), flush=True)
    print("LAN address: http://{}:{}".format(config["mac_ip"], port), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
