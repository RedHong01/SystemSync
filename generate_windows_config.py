#!/usr/bin/env python3
import json
from pathlib import Path

from server import load_config


APP_DIR = Path(__file__).resolve().parent
OUTPUT = APP_DIR / "windows" / "agent-config.generated.json"


def main():
    config = load_config()
    payload = {
        "DashboardUrl": "http://{}:{}".format(config["mac_ip"], config["listen_port"]),
        "Token": config["shared_token"],
        "Port": config["remote_agent_port"],
        "ProjectBase": config["remote_project_base"],
        "SyncthingGuiUrl": config["syncthing_url"],
        "MacDeviceId": config["local_device_id"],
        "WindowsDeviceId": config["remote_device_id"],
        "MacMac": config["mac_mac"],
        "MacIp": config["mac_ip"],
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
