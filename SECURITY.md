# 安全 / Security

本项目设计用于可信任的本地局域网。

This project is intended for trusted local networks.

## 不要暴露到公网 / Do Not Expose It to the Public Internet

控制台可以触发本地文件操作、Syncthing 配置变更和 Wake-on-LAN 数据包。请只在可信局域网内运行，或放在你自己控制的 VPN 后面。

The dashboard can trigger local file operations, Syncthing configuration changes, and Wake-on-LAN packets. Run it only on a trusted LAN or behind your own VPN.

## 密钥与私有配置 / Secrets

不要提交：

Do not commit:

- `config.json`
- `runtime-state.json`
- `windows/agent-config.generated.json`
- Syncthing API keys
- shared companion tokens

这些文件默认已被 `.gitignore` 忽略。

These files are ignored by default.

## 报告安全问题 / Reporting Issues

社区版本中，如果发现安全问题，请先私下联系仓库维护者，再创建公开 issue。

For community releases, report security issues privately to the repository maintainer before opening a public issue.
