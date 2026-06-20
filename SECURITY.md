# Security

This project is intended for trusted local networks.

## Do not expose it to the public internet

The dashboard can trigger local file operations, Syncthing configuration changes, and Wake-on-LAN packets. Run it only on a trusted LAN or behind your own VPN.

## Secrets

Do not commit:

- `config.json`
- `runtime-state.json`
- `windows/agent-config.generated.json`
- Syncthing API keys
- shared companion tokens

These files are ignored by default.

## Reporting issues

For community releases, report security issues privately to the repository maintainer before opening a public issue.
