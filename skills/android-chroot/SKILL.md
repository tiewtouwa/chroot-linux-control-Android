---
name: android-chroot
description: 在已 root 的 Android chroot 中操作手机：USB 网卡与网络共享、IP/路由/DNS、nmap 扫描、SSH/文件传输/隧道、抓包、防火墙，以及应用管理、界面操作、相机音频、红外/NFC、传感器和系统自动化。不用于 proot 安装或刷机。
---

# Android chroot

用中文简短回复，复用现有 chroot，按用户目标调用本机接口。下列脚本命令从技能目录执行。

首次连接或换手机，先用 `sh scripts/android-shell.sh --check` 确认通路，再读取任务所需的型号、用户、网络或硬件信息。完整环境核查用 `python3 scripts/phone.py doctor`；普通查询不必每次导出界面。包名、网卡名、坐标、IP、驱动和文件路径都从当前设备取得，不沿用其他机型结果。

## 按任务加载

只读当前任务对应的文档；用户要求盘点全部能力时再遍历各类入口。

| 用户目标 | 入口与操作说明 |
|---|---|
| USB 网卡、修改 IP、路由／DNS、USB 共享／反向供网、Wi-Fi／蓝牙共享、NAT | [网络配置](references/networking.md) |
| nmap、SSH 登录电脑／手机、SCP／SFTP／rsync、端口转发／SOCKS、测速、抓包 | [远程与网络工具](references/remote-access.md) |
| 声音、语音、拍照／录音、手电筒、震动、红外、NFC、传感器、定位、剪贴板 | [手机硬件与系统接口](references/device-interfaces.md) |
| 通知、短信／电话、联系人、壁纸／显示、电源、文件分享、定时任务、指纹认证 | 同上 |
| 应用清单、批量禁用、原状态恢复、重启前后对比 | [应用管理](references/package-management.md) |
| 按文字／ID 点击、等待界面、验证结果、截图与前台应用 | [界面操作](references/ui-operations.md) |
| 电池、显示参数等原生命令 | [操作示例](references/phone-operations.md) |
| 动态库、Binder、Termux API、权限和挂载问题 | [连接排障](references/android-bridge.md) |

## 执行与验证

- 用户要求盘点／检查时只读；修改、扫描范围、远程登录、通信发送按本次及已有授权执行。已明确授权的内容无需重复确认；编写技能不等于立即启动所有功能。
- 区分硬件声明、工具存在、接口响应和实际效果。缺依赖就说明，依任务需要安装；不把全部功能列为默认安装项。远端未配合、没有凭据或外设未连接时报告尚缺的条件。
- Android 系统命令走 `android-shell.sh`，Linux 网络工具在 chroot 运行，Termux API 使用已有通路。参数以 argv 传递，不把外部文本插入 shell 源码；不自动开放远程服务或关闭 SELinux。
- 网络改动前核对当前会话出口和目标接口，保存原状态；操作后核对双向连通性，回滚仅撤销本次改动。USB 配置成功不代表网卡已起链路，手机自身联网不代表共享客户端联网。
- 应用修改前保存原状态并核对 Android 用户；UI 先观察再定位，多个匹配或落点冲突不点击。命令已发送不等于任务完成；验证失败先检查实际状态，不自动重复有副作用的操作。
- 拍照、录音、定位、拨号、短信、指纹弹窗不用于连通性自检。传感器、抓包、扫描和后台任务限定范围、时长或次数；记录本次进程／任务及停止方法。
- 状态、截图、媒体、抓包、网络配置和凭据不进入仓库。脚本默认记录位于 `~/.local/state/android-chroot/`；Termux 写文件另选应用可访问的仓库外路径。输出只包含任务需要的信息，图片需查看后再描述。
