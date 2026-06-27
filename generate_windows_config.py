#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import secrets

from server import DEFAULT_CONFIG, dashboard_alias, local_ip_candidates


APP_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT = APP_DIR / "windows" / "agent-config.generated.json"
CONFIG_CANDIDATES = [
    APP_DIR / "config.json",
    Path.home() / "Library/Application Support/SystemSync/config.json",
    Path.home() / "Library/Application Support/RedLanSyncDashboard/config.json",
]


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def save_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(path)


def resolve_config_path(explicit: str = "") -> Path:
    candidates = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    env_path = os.environ.get("SYSTEMSYNC_CONFIG")
    if env_path:
        candidates.append(Path(env_path).expanduser())
    candidates.extend(CONFIG_CANDIDATES)
    for candidate in candidates:
        if candidate and candidate.exists():
            return candidate.resolve()
    return CONFIG_CANDIDATES[0].resolve()


def load_config(path: Path) -> dict:
    config = DEFAULT_CONFIG.copy()
    stored = load_json(path)
    config.update(stored)
    changed = False
    if not config.get("shared_token"):
        config["shared_token"] = secrets.token_urlsafe(32)
        changed = True
    if not stored.get("github_repo"):
        config["github_repo"] = "RedHong01/SystemSync"
        changed = True
    if config.get("current_version") != DEFAULT_CONFIG.get("current_version") and not stored.get("current_version"):
        config["current_version"] = DEFAULT_CONFIG.get("current_version")
        changed = True
    if changed or not path.exists():
        save_json(path, {**stored, **config})
    return config


def resolve_mac_ip(config: dict, config_path: Path) -> str:
    mac_ip = str(config.get("mac_ip") or "").strip()
    if mac_ip:
        return mac_ip
    candidates = local_ip_candidates(config)
    if not candidates:
        return ""
    mac_ip = candidates[0]
    config["mac_ip"] = mac_ip
    stored = load_json(config_path)
    stored["mac_ip"] = mac_ip
    save_json(config_path, {**config, **stored})
    return mac_ip


def auth_url(base_url: str, token: str) -> str:
    from urllib.parse import quote

    return base_url.rstrip("/") + "/auth?token=" + quote(token, safe="")


def write_windows_url_shortcut(path: Path, url: str) -> None:
    path.write_text(
        "[InternetShortcut]\n"
        f"URL={url}\n"
        "IconFile=%SystemRoot%\\System32\\shell32.dll\n"
        "IconIndex=13\n",
        encoding="ascii",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the paired Windows companion config for SystemSync.")
    parser.add_argument("--config", help="Path to the SystemSync config.json. Defaults to repo config, then installed SystemSync config, then legacy config.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output agent-config.generated.json path.")
    args = parser.parse_args()

    config_path = resolve_config_path(args.config or "")
    config = load_config(config_path)
    mac_ip = resolve_mac_ip(config, config_path)
    alias = dashboard_alias(config)
    payload = {
        "DashboardUrl": "http://{}:{}".format(mac_ip, config["listen_port"]),
        "DashboardAlias": alias,
        "DashboardAliasUrl": "http://{}:{}".format(alias, config["listen_port"]) if alias else "",
        "Token": config["shared_token"],
        "Port": config["remote_agent_port"],
        "ProjectBase": config["remote_project_base"],
        "SyncthingGuiUrl": config["syncthing_url"],
        "MacDeviceId": config["local_device_id"],
        "WindowsDeviceId": config["remote_device_id"],
        "MacMac": config["mac_mac"],
        "MacIp": mac_ip,
    }
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    shortcut = output.with_name("OpenSystemSyncDashboard.generated.url")
    write_windows_url_shortcut(shortcut, auth_url(payload["DashboardUrl"], payload["Token"]))
    print("config:", config_path)
    print("output:", output)
    print("shortcut:", shortcut)
    print("dashboard:", payload["DashboardUrl"])
    if payload["DashboardAliasUrl"]:
        print("alias:", payload["DashboardAliasUrl"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
