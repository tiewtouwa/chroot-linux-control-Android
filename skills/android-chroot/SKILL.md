---
name: android-chroot
description: 在真实 root 的 Android chroot 中控制手机，检查环境、管理应用禁用与恢复、对比重启状态、按界面文字或 ID 操作、截图和查询前台应用。不用于 proot 安装或刷机。
---

# Android chroot

用中文简短回复，复用现有 chroot，只执行用户要求的操作。下面命令在技能目录执行。

首次连接或换手机，先运行 `python3 scripts/phone.py doctor`。核对本次型号、系统、用户和可用接口；UID 0 不代表所有 Android 服务都可访问。包名、控件 ID、坐标、截图目录不能沿用其他机型的结果。

按任务选择：

| 任务 | 入口 |
|---|---|
| 环境与服务自检 | `python3 scripts/phone.py doctor` |
| 应用清单、批量禁用、精确恢复 | 先读 [应用管理](references/package-management.md) |
| 重启前后状态对比 | 同上，使用 `snapshot` / `compare`；仅在用户要求时重启 |
| 文字／ID 定位、点击与结果验证 | 先读 [界面操作](references/ui-operations.md) |
| 实时截图、前台应用 | `python3 scripts/phone.py screenshot` / `foreground`，细节见界面操作 |
| 其他系统命令 | `sh scripts/android-shell.sh -c 'dumpsys battery'`；见 [操作示例](references/phone-operations.md) |

- 用户要求清单或检查时只读；禁用、恢复、点击按本次及已有授权执行。已明确授权的范围无需重复确认；增加技能不等于授权实际禁用应用或重启手机。
- 应用修改前保存原状态，修改后读取真实状态核验。只操作已确认的包和 Android 用户；中途失败先读记录，不盲目重跑整批。
- UI 操作先观察再定位；多个匹配目标不点击。点击后验证预期页面，命令已发送不等于任务已完成，验证失败不自动再点。
- 优先使用 Android shell。参数通过位置参数传递，不插入 shell 源码。Termux API 或已有 ADB 仅按需使用，不自动开放远程服务。
- 状态记录和截图默认放在 `~/.local/state/android-chroot/`，不覆盖已有文件，不进入仓库。截图必须查看，旧截图不代表实时页面；分享输出前去除手机数据与凭据。
- 不为排障关闭 SELinux 或扩大权限；未验证的结果不声称成功。失败时读 [连接排障](references/android-bridge.md)。
