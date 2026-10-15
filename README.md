# Android chroot 手机技能

面向已 root 的 ARM Android 手机，在 chroot Linux 中使用 Codex 操作手机。主要入口为 `$android-chroot`，支持检查现有 Android shell、调用系统服务、按任务使用 Termux:API、操作应用/屏幕以及排查挂载与权限。

proot 是无 root 运行 Linux 用户空间的方式，其模拟 root 不增加 Android 权限。本仓库仅实现 chroot 技能。

## 安装与调用

把 `skills/android-chroot` 文件夹复制到 `~/.agents/skills/android-chroot`。如果目标已存在，先检查差异再更新。遵循当前客户端的技能目录配置；[官方技能文档](https://learn.chatgpt.com/docs/build-skills)说明了本地发现路径和调用方式。

在 Codex 中输入：

```text
$android-chroot 检查手机连接和权限，然后读取电池状态
```

若技能列表尚未刷新，重新启动 Codex。安装技能提供操作流程，不会自动赋予 root、建立远程连接或安装 Termux:API。

## 内容

- `skills/android-chroot/SKILL.md`：入口与执行规则。
- `skills/android-chroot/scripts/android-shell.sh`：复用现有 Android shell 的命令包装与只读检查。
- `skills/android-chroot/references/`：连接排障和手机操作参考。

只读自检：

```sh
sh skills/android-chroot/scripts/android-shell.sh --check
```

包装脚本要求现有环境可执行 `/system/bin/sh`；不会自动挂载、提权或连接设备。相机、麦克风、定位等仍依赖具体接口与 Android 权限。

仓库不保存手机数据、截图、密钥或访问令牌。
