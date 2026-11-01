# 界面查询、点击与截图

从技能目录执行。先读取当前页面，不复用另一手机或旧页面的坐标。

```sh
python3 scripts/phone.py foreground
python3 scripts/ui-controls.py --json
python3 scripts/ui-controls.py --text '设置' --exact --json
python3 scripts/ui-controls.py --id '实际控件ID' --exact --wait 5 --json
```

输出包含文字、ID、所属包、范围、中心坐标、节点自身的可用／可点击／可长按／勾选状态。父容器禁用不递归改变子节点状态；`tap_center` 和 `tap_error` 单独表示实际落点是否可用。`--text` 和 `--id` 可以组合；默认包含匹配，`--exact` 精确匹配。密码控件及其子树不输出。游戏、自绘页面可能没有可查询控件。

## 点击并验证

以下是语法示例，文字和 ID 应取自本次实际页面：

```sh
python3 scripts/ui-controls.py --text '设置' --id '实际控件ID' --exact --click --expect-text '新页面标题' --wait 5
```

只允许唯一、可用的目标；文字所在子控件不可点击时，检查最近的可点击或可长按父控件。实际点击目标必须自身启用且范围有效，不跨过禁用或仅支持长按的触摸接收节点向外寻找；此命令只发送短点击，不把它转成长按。中心落点若被其他可点击或可长按控件占用，或这些控件范围不明，则拒绝点击；无文字、已禁用及密码控件也参与占位检查，但不输出密码内容。此检查不根据 XML 顺序猜测遮挡层级，可能保守拒绝部分可操作页面。发送点击前重新导出页面并检查落点；目标的状态、包和坐标发生变化就停止。点击仅发送一次，之后轮询新出现的 `--expect-text`／`--expect-id`；两个条件组合时必须匹配同一个控件。

预期目标在点击前已存在时拒绝点击，因为它不能证明此次操作成功。选择能代表目标页面的具体标题或 ID；匹配成功只证明该界面条件成立，实际保存、发送等业务结果仍需另查。XML 无法完整描述自定义触摸处理，落点检查也不保证应用实际分发结果。

不带预期条件也可点击，但报告 `verified: false` 并返回 3；随后通过界面、截图或相关服务验证。错误／超时可能发生在点击已发送之后，先观察，不自动重试。返回码：0 查询或条件验证成功；1 无匹配；2 错误；3 点击已发送但结果未验证。

## 实时截图和已保存截图

```sh
python3 scripts/phone.py screenshot
python3 scripts/phone.py screenshot --output /absolute/path/outside/repo/screen.png
```

默认保存到 `~/.local/state/android-chroot/` 下唯一文件，检查 PNG 头与尺寸；随后用图像工具查看返回路径，确认页面内容，受保护页面可能黑屏。脚本不假设系统截图相册路径，不覆盖已有文件。截图敏感信息可能来自当前页面，完成后按用户需要保留或清理。

用户要求读取系统已保存截图时，先检查本机共享存储可见性和实际目录，再按修改时间选择并查看；不要将 `/sdcard/Pictures/Screenshots` 当作所有机型的固定路径。

`foreground` 列出当前 resumed Activity 的用户和组件；多窗口可能返回多项，锁屏时可能无法识别。它不能证明该应用正在接收全部触摸事件。
