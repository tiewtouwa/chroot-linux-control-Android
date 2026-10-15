---
name: android-chroot
description: 在有真实 root 的 Android chroot Linux 环境中控制手机、调用 Android 系统命令或 Termux API、操作应用与屏幕、管理文件并排查权限和挂载问题。用户主要使用 chroot，手机操作默认优先检查此路径；不用于普通 Linux 管理或无 root 的 proot 安装。
---

# Android chroot 手机控制

用户主要在已 root 的 ARM Android 手机上运行 chroot Linux。默认沿用已有 chroot 和手机连接，不重新安装 Linux，也不先切换到 ADB。用中文沟通；根据具体任务执行并验证结果。

## 确认当前执行位置

首次操作或连接变化后，检查 `uname -m`、`id`、`/proc/self/status` 中的能力字段，以及 `/system/bin/sh`、`/system/bin/cmd` 是否可访问。不要把云端 Linux、另一台设备或普通容器误当成本机手机。

在技能目录运行只读探测：

```sh
sh scripts/android-shell.sh --check
```

脚本检查 Android shell 身份、系统版本和架构。成功只表示 Android 命令通路可用，不代表所有系统服务或硬件权限可用；失败时保留错误并按 [连接与排障](references/android-bridge.md) 检查，不自动更改挂载或 SELinux。

Linux 的 `id` 显示 0 不能单独证明 Android 控制权限。结合用户已确认的真实 root、Android shell 身份、能力与目标命令结果判断。proot 只模拟 Linux 用户空间中的 root，不会赋予 Android root；本技能不实现 proot 流程。

## 选择执行通路

1. **Android 系统命令**：当前 chroot 能直接运行 Android shell 时，使用 `scripts/android-shell.sh -c '固定命令'`。它在子进程内隔离 Linux 动态库环境并使用 Android PATH，避免混用两套系统的同名工具。通过参数传值，不把文件名、包名或用户输入拼进 shell 源码。
2. **Termux:API**：定位、相机、录音、传感器等任务使用已安装的 Termux:API 及其应用权限，优先复用已验证的 Termux 执行通路。root 不替代应用权限，chroot 里能看到 `termux-*` 文件不代表跨 UID 调用可用。
3. **ADB**：当前通路不可用或用户指定 ADB 时才使用已有授权连接；多设备时指定序列号。不要为调用系统命令自动开放网络 ADB 或新建远程控制服务。

命令示例和结果核对见 [手机操作](references/phone-operations.md)。按需查目标设备自己的 `help`，不假设所有 Android 版本和厂商参数相同。

## 执行和验证

- 确定操作对象：应用包名和 Android 用户/工作资料、手机与 chroot 的路径映射、屏幕尺寸/旋转和当前页面。参数明确且已有授权时直接继续，不反复确认。
- UI 操作采用“观察页面 → 小步操作 → 再观察”。只在任务需要时截图，不把点击命令返回 0 当作操作完成。中文输入不要假设 `input text` 支持，选择已有的输入法或自动化通路。
- 修改设置或应用状态前记录相关旧值，完成后用针对性查询核对；只读任务不改变设备状态。相机、麦克风、位置、联系人仅在任务确实需要时访问，不作为连通性测试。
- 发送消息、拨号、支付、删除数据、刷机等动作必须属于用户明确授权的具体任务；创建或调用此 skill 本身不构成这些操作的授权。已有授权覆盖的正常步骤直接完成。
- 权限失败时检查原始错误、UID/SELinux、Android 服务和挂载可见性。不用 `setenforce 0`、递归 chmod、系统分区重挂载或无限重试作为通用修复。
- 最后说明实际完成的动作、验证结果和仍不可用的能力；未测试的硬件或 UI 功能不能报告为已验证。

## 保存与分享

技能仓库只保存通用指令、脚本和必要文档。手机截图、录音、联系人、应用数据、设备标识、访问令牌和 SSH/ADB 密钥留在任务指定位置，不随技能提交；私有仓库也遵守此边界。
