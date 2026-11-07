---
name: android-chroot
description: 在已 root 的 Android chroot 中操作手机：USB 网卡与网络共享、IP/路由/DNS、nmap 扫描、SSH/文件传输/隧道、抓包、防火墙，以及应用与进程查询、界面操作、相机音频、红外/NFC、传感器和系统自动化。不用于 proot 安装或刷机。
---

# Android chroot

用中文简短回复，复用现有 chroot，按用户目标调用本机接口。下列脚本命令从技能目录执行。

首次连接或换手机，先用 `sh scripts/android-shell.sh --check` 确认通路，再读取任务所需的型号、用户、网络或硬件信息。完整环境核查用 `python3 scripts/phone.py doctor`；普通查询不必每次导出界面。包名、网卡名、坐标、IP、驱动和文件路径都从当前设备取得，不沿用其他机型结果。

## 操作索引

按目标读取对应章节，不遍历全部文档。常用只读入口：`python3 scripts/phone.py foreground` 查前台，`python3 scripts/ui-controls.py --json` 查控件，`python3 scripts/phone.py screenshot` 截图。参数用脚本 `--help` 查询。

| 用户目标 | 入口与操作说明 |
|---|---|
| USB 网卡、修改 IP、路由／DNS、USB 共享／反向供网、Wi-Fi／蓝牙共享、NAT | [网络配置](references/networking.md) |
| nmap、SSH 登录电脑／手机、SCP／SFTP／rsync、端口转发／SOCKS、测速、抓包 | [远程与网络工具](references/remote-access.md) |
| 启动应用、输入文字、滑动／按键、录屏、亮度／旋转、通知栏 | [应用与屏幕](references/device-interfaces.md#应用界面屏幕) |
| 音量、播放、语音、拍照／录音 | [媒体](references/device-interfaces.md#声音语音相机和录音) |
| 手电筒、震动、红外、NFC 标签 | [硬件](references/device-interfaces.md#手电筒震动红外nfc) |
| 传感器、定位、剪贴板 | [采集与剪贴板](references/device-interfaces.md#传感器定位与剪贴板) |
| 通知、勿扰、短信／电话、联系人 | [通知与通信](references/device-interfaces.md#通知对话框与通信) |
| 壁纸、深色模式、电池、省电、亮屏／息屏、重启 | [外观与电源](references/device-interfaces.md#壁纸外观电池与电源) |
| 文件选择／分享、下载、SAF、USB 外设 | [文件与外设](references/device-interfaces.md#文件访问下载分享与-usb-外设) |
| 定时任务、闹钟、指纹认证、Keystore | [自动化与认证](references/device-interfaces.md#定时任务闹钟与指纹密钥) |
| 应用清单、批量禁用、原状态恢复、重启前后对比 | [应用管理](references/package-management.md)：`phone.py packages/disable/restore/snapshot/compare` |
| 按文字／ID 点击、等待界面、验证结果、截图与前台应用 | [界面操作](references/ui-operations.md) |
| Android 进程、PID、资源占用、用户、显示参数、文件路径检查 | [原生命令示例](references/phone-operations.md) |
| 动态库、Binder、Termux API、权限和挂载问题 | [连接排障](references/android-bridge.md) |

调用 `termux-*` 前读[调用准备](references/device-interfaces.md#调用准备)，复用现有通路。

## 执行与验证

- 用户要求盘点／检查时只读；修改、扫描范围、远程登录、通信发送按本次及已有授权执行。已明确授权的内容无需重复确认；编写技能不等于立即启动所有功能。
- 区分硬件声明、工具存在、接口响应和实际效果。缺依赖就说明，依任务需要安装；不把全部功能列为默认安装项。远端未配合、没有凭据或外设未连接时报告尚缺的条件。
- Android 系统命令走 `android-shell.sh`，Linux 网络工具在 chroot 运行，Termux API 使用已有通路。参数以 argv 传递，不把外部文本插入 shell 源码；不自动开放远程服务或关闭 SELinux。
- 网络改动前核对当前会话出口和目标接口，保存原状态；操作后核对双向连通性，回滚仅撤销本次改动。USB 配置成功不代表网卡已起链路，手机自身联网不代表共享客户端联网。
- 应用修改前保存原状态并核对 Android 用户；UI 先观察再定位，多个匹配或落点冲突不点击。命令已发送不等于任务完成；验证失败先检查实际状态，不自动重复有副作用的操作。
- 拍照、录音、定位、拨号、短信、指纹弹窗不用于连通性自检。传感器、抓包、扫描和后台任务限定范围、时长或次数；记录本次进程／任务及停止方法。
- 状态、截图、媒体、抓包、网络配置和凭据不进入仓库。脚本默认记录位于 `~/.local/state/android-chroot/`；Termux 写文件另选应用可访问的仓库外路径。输出只包含任务需要的信息，图片需查看后再描述。
