# 应用状态与恢复

所有命令从技能目录执行。先查 `sh scripts/android-shell.sh -c 'am get-current-user'`，以下 `--user 0` 仅是示例，替换为已确认的用户。`phone.py` 默认将记录写到仓库外的 `~/.local/state/android-chroot/`，权限 600；输出会显示实际路径。

## 清单和禁用

```sh
python3 scripts/phone.py packages --user 0
python3 scripts/phone.py packages --user 0 com.example.app
python3 scripts/phone.py disable --user 0 com.example.app com.example.other
```

清单给出 enabled 原始值、实际 disabled 状态、stopped、hidden、suspended。脚本不凭包名猜广告或安全性；执行禁用前结合包信息与用户用途确定清单。尤其核对当前桌面、输入法和提供当前连接的应用，避免中断操作。

禁用会先验证所有目标并保存原始 enabled 状态，再逐项执行 `pm disable-user`、读取结果；失败立即停止后续项，已完成的项目及错误保留在恢复记录中。不会卸载 APK 或清除数据。

## 恢复

```sh
python3 scripts/phone.py restore --user 0 /absolute/path/to/disable-record.json
```

仅使用本工具创建的可信本地记录。恢复前解析记录的真实路径，读取和更新均使用该路径；通过软链接恢复不会替换链接，原文件也会写入 restored 标记。断开的链接在修改应用前报错。恢复核对设备身份摘要和用户，分别还原 default-state、enable、disable、disable-user、disable-until-used。原本已 disabled-user 的包不会被重新启用；未尝试修改或已经标记 restored 的包跳过。其余项目如果目前状态既非本次禁用状态也非原状态，则停止，避免覆盖后续改动。部分恢复后可以重跑同一记录，仅继续未完成项，不影响已恢复项后续的禁用操作。此恢复只还原包级 enabled 状态，不恢复进程、组件开关、数据或其他系统设置。

## 重启前后对比

```sh
python3 scripts/phone.py snapshot --user 0
# 保存上一步返回的路径。用户已要求重启时，才通过现有通路执行重启。
# 重连后：
python3 scripts/phone.py compare --user 0 /absolute/path/to/snapshot.json
```

快照包含设备身份摘要、系统版本、boot ID、用户及应用状态。对比报告是否真的重启、系统版本是否变化、增删应用和状态差异。没有重启也可比较，报告会显示 `rebooted: false`。

- enabled：0 默认、1 显式启用、2 禁用、3 用户禁用、4 使用前禁用。0 并不总等于可用，还要看清单中的 disabled。
- disabled 从包管理器单独查询；stopped 表示包的停止标志，不等于 disabled，也不等于完整的进程存活检测。
- boot ID 或 stopped 变化不能单独证明包重新启用。以 enabled 与 disabled 的前后值判断；应用更新、组件状态及 ROM 管理策略需要另查。
- 对比只报告变化，不自动重新禁用。
