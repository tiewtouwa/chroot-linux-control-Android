# chroot-linux-control-Android

让 Codex 在已 root 的 Android chroot Linux 中操作手机，并作为网络诊断、USB 共享和 SSH 终端使用。核心是 `android-chroot` skill；proot 仅作说明。

当前版本：`v0.3.1`。

## 安装与调用

需要现有 root/chroot 环境和可用的 Android 接口。技能不会授予权限，也不自动安装工具或启动服务。

在项目根目录建立软链接：

```sh
mkdir -p "$HOME/.agents/skills"
ln -s "$(pwd)/skills/android-chroot" "$HOME/.agents/skills/android-chroot"
```

目标已存在时先检查，不强制覆盖。也可复制 `skills/android-chroot` 到技能目录。软链接随工作区更新；版本通过 Git 标签管理，技能名保持 `android-chroot`。

在 Codex 中直接描述任务，或明确调用：

```text
$android-chroot 检查 USB 网络共享，确认对端有没有取得地址
$android-chroot 查看这台手机有哪些网卡和网络工具
$android-chroot 用我已有的 SSH 配置连接指定电脑
$android-chroot 查看支持的红外频率和传感器
```

首次加载未出现时重启 Codex。使用某项能力时只加载对应操作文档，不为普通查询执行完整硬件测试。

## 功能范围

| 类别 | 能力 | 操作说明 |
|---|---|---|
| USB 网络 | 外接网卡识别、驱动与链路检查、手机 USB 共享、电脑反向供网 | [网络配置](skills/android-chroot/references/networking.md) |
| 地址与路由 | IP／掩码、DHCP 检查、策略路由、DNS、代理诊断 | 同上 |
| 无线与转发 | Wi-Fi 连接／热点、蓝牙 PAN、飞行模式、NAT、防火墙 | 同上 |
| 网络工具 | 主机发现、端口扫描、连通性、测速、网卡状态、抓包 | [远程与网络工具](skills/android-chroot/references/remote-access.md) |
| SSH 与文件 | 登录电脑、手机 SSH 服务、SCP／SFTP／rsync、隧道、SOCKS 代理 | 同上 |
| 应用管理 | 包清单、批量禁用、原状态恢复、重启前后对比 | [应用管理](skills/android-chroot/references/package-management.md) |
| 界面与屏幕 | 前台应用、文字／ID 定位、点击验证、滑动、按键、截图、录屏 | [界面操作](skills/android-chroot/references/ui-operations.md) · [系统接口](skills/android-chroot/references/device-interfaces.md) |
| 媒体与硬件 | 音量、播放、语音播报／识别、拍照、录音、手电筒、震动 | [系统接口](skills/android-chroot/references/device-interfaces.md) |
| 传感与通信 | 红外、NFC、传感器、定位、剪贴板、通知、短信、电话、联系人 | 同上 |
| 外观与电源 | 亮度、旋转、显示模式、壁纸、深色模式、电池、省电、唤醒、重启 | 同上 |
| 文件与自动化 | 文件选择／分享、SAF、下载、媒体扫描、USB 外设、计划任务、闹钟、指纹认证、Keystore | 同上 |

具体支持取决于手机内核、ROM、权限和对端。工具存在、接口可查询和操作成功分别验证；文档覆盖不代表每种动作都已在所有设备实测。没有红外接收器不能学习遥控码，打开 USB 网卡功能也不等于完成网络共享。

## 依赖与执行方式

- 原生 Android：复用 `/system/bin/sh` 和 `cmd`、`dumpsys`、`pm`、`input` 等。包装脚本在子进程清理 Linux 动态库变量。
- chroot：已有功能脚本需要 Python 3 标准库；网络任务按需使用 `ip`、OpenSSH、nmap、tcpdump、iperf3 等，先检查是否安装。Debian 环境中的通用工具优先用 Debian apt 安装并调用，核对命令路径，避免混用 Termux 版本。
- Termux:API：需要兼容的应用、命令行工具、权限及可用调用通路。相机、录音、定位、短信等不用于自检。
- Android 防火墙优先使用原生命令；chroot 的 nft 后端或扩展库可能不兼容。连接问题见 [连接排障](skills/android-chroot/references/android-bridge.md)。

在技能目录运行：

```sh
python3 scripts/phone.py doctor
python3 scripts/phone.py foreground
python3 scripts/ui-controls.py --text '设置' --exact --json
```

`phone.py` 提供自检、应用状态、恢复、快照对比、截图和前台查询。其余能力由 skill 按对应文档调用本机工具，不要求每项功能都增加一层包装脚本。

## 本地数据

应用状态记录和脚本截图默认写到 `~/.local/state/android-chroot/`，不进入仓库；Termux 应用生成的媒体文件需另选它可写的仓库外路径。不要提交真实设备标识、网络配置、通讯录、抓包、照片或凭据。

禁用前保存原状态；恢复核对设备和用户，跳过已完成项。UI 点击检查唯一目标、当前状态及落点冲突，结果验证失败不自动重试。网络修改先记录原值，仅撤销本次变化。

## 震动通知

- `sh scripts/vibrate.sh 500`：震动 500 毫秒；执行失败会保留错误和退出码。
- `codex_notify_filter.py`：过滤子任务完成通知。
- `scripts/agy_vibrate_on_stop.sh`：agy Stop hook，调用同目录的 Python 脚本，仅在 `fullyIdle=true`、`terminationReason=model_stop` 且无错误时震动；输出空 JSON。

通知脚本需要本机 `cmd vibrator_manager` 和相应权限；脚本执行成功不替代硬件效果验证。

## 验证与版本

在项目根目录运行模拟测试，不操作真实手机：

```sh
python3 -m unittest discover -s skills/android-chroot/tests -v
python3 -m unittest discover -s scripts -p 'test_*.py' -v
```

真实设备验证按任务选择只读入口；实际禁用、拍照、录音、网络切换和连接对端分别在对应操作请求下测试。发布使用 Git 标签；新增功能更新次版本，问题修复更新补丁版本，不把版本号加进技能名。

提交前阅读 [隐私与提交规则](AGENTS.md)。许可证：[MIT](LICENSE)。
