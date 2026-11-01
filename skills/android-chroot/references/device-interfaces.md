# 手机硬件与系统接口

适用于媒体、相机、录音、红外、NFC、传感器、通信、通知和自动化。UI 定位见 [界面操作](ui-operations.md)，应用禁用／恢复见 [应用管理](package-management.md)。

## 调用准备

先用 `command -v` 查本次需要的 `termux-*` 命令，再确认 `com.termux.api` 应用存在。应用安装、命令存在、权限已授予、实际执行成功是不同状态，不能互相代替。优先复用当前 Termux 通路。

在技能目录可定义两个调用函数，动态库清理只影响子进程：

```sh
android() { sh scripts/android-shell.sh -c 'exec "$@"' android "$@"; }
termux_api() (
    unset LD_LIBRARY_PATH LD_PRELOAD LD_AUDIT
    "$@"
)
```

Termux 不在 PATH 时，查找现有安装并使用其真实命令路径，不为此切换 UID、安装另一个包或启动远程服务。需要验证 API 通路时，用有超时的电池查询；不要用拍照、录音、定位、发送消息或指纹弹窗测试连通性。

先读对应本地脚本的 usage 或支持的帮助选项，不假设每个程序都支持 `--help`。多数 `termux-*` 是可直接查看的 shell 脚本。超时只说明调用未返回，操作可能已开始；先核对当前状态，再决定重试。

输出文件保存在仓库外。需要 Termux 应用写文件时，使用已授权且应用可见的共享存储路径，先确认映射和空闲空间，不能直接使用只有 chroot root 可访问的 `/root` 路径。避免覆盖已有文件。

## 应用、界面、屏幕

| 功能 | 操作入口 | 验证 |
|---|---|---|
| 启动应用、打开网页／文件 | `am start`、`termux-open-url`、`termux-open`；先解析本机包名和 Activity，参数以 argv 传递 | `phone.py foreground` 和实际页面 |
| 应用清单、禁用、恢复、重启对比 | `phone.py packages/disable/restore/snapshot/compare` | 按应用管理文档核对原状态、设备和用户 |
| 文字／ID 点击 | `ui-controls.py`；歧义或落点冲突时停止 | 预期界面条件及业务结果 |
| 滑动、按键、长按 | 原生 `input`，先读本机帮助；有长按参数时按其语法调用，不能把普通短点击称为长按 | 操作后重新读取界面 |
| 输入文本 | 优先输入法／应用自身接口；剪贴板粘贴仅在用户要求输入时使用 | 核对文本和焦点；`input text` 不能假定支持中文 |
| 截图、前台应用 | `phone.py screenshot/foreground` | 查看截图；前台 Activity 不等于所有触摸都发给它 |
| 录屏 | `screenrecord --help`；按请求指定时长、尺寸和输出文件 | 命令结束后检查视频时长及可播放性；原生录屏不默认包含音频 |
| 亮度 | `termux-brightness` 或本机 `cmd display set-brightness` | 两者数值单位可能不同，先查帮助；核对自动亮度模式 |
| 旋转、分辨率、密度、刷新率 | `cmd window help`、`cmd display help` | 记录旧值；仅选择实际支持的显示模式，核对应用后的状态 |
| 通知栏、快捷设置 | `cmd statusbar expand-notifications/expand-settings/collapse`；点磁贴前识别组件 | 实际页面与对应开关状态 |

不要通过猜测坐标处理系统授权弹窗。权限不足时描述缺少的权限，按用户目标通过系统正常授权流程处理。

## 声音、语音、相机和录音

- **音量／音频路由**：`termux-volume` 无参数查询流及范围，`termux-volume music "$LEVEL"` 修改指定流；`termux-audio-info` 查音频能力。铃声、闹钟、媒体、通话流分开处理，保存原值。
- **媒体播放**：`termux-media-player info` 查询；按请求用 `play "$FILE"`、`pause`、`stop`。控制其他应用播放时，先查 `cmd media_session help` 和当前会话，再发送其支持的媒体按键。存在会话不等于正在播放。
- **语音播报**：`termux-tts-engines` 查询引擎，`termux-tts-speak -l zh "$TEXT"` 播报。语言是否可用取决于当前引擎和语音包；不凭请求已提交声称已听到声音。
- **语音识别**：`termux-speech-to-text` 会启动语音输入，可能输出多次部分结果。只在用户要求听写时启动，区分部分和最终文本，结束后确认停止。
- **拍照**：先查 `termux-camera-info` 的实际相机 ID，按请求执行 `termux-camera-photo -c "$CAMERA_ID" "$OUTPUT"`。验证生成的是本次图片并查看；相机占用、权限和后台限制需要单独处理。
- **录音**：`termux-microphone-record -i` 查状态；使用下面经校验的固定时长调用，`-q` 停止。不结束他人已在进行的录音。检查结束状态、文件和实际时长。

运行前按用户要求设置 `RECORD_DURATION_SECONDS` 和应用可写的 `OUTPUT`，不能使用 Bash 内置计时变量 `SECONDS`。时长须为不带前导零的正整数；上限避免秒转毫秒后超出 API 的有符号 32 位整数范围。0 表示无限录音，以下示例明确拒绝。

```bash
(
    if ! [[ ${RECORD_DURATION_SECONDS-} =~ ^[1-9][0-9]{0,6}$ ]] ||
       (( RECORD_DURATION_SECONDS > 2147483 )); then
        printf '%s\n' 'RECORD_DURATION_SECONDS 必须为 1–2147483 的整数秒' >&2
        exit 2
    fi
    termux_api termux-microphone-record -f "$OUTPUT" -l "$RECORD_DURATION_SECONDS"
)
```

录音、识别、相机调用可能受 Android 后台权限限制。不能通过关闭系统隐私保护、SELinux 或伪造前台状态来绕过。

## 手电筒、震动、红外、NFC

- **手电筒**：`termux-torch on`／`off`。按请求启停，先确认是否由相机占用，不能把命令返回当作已观察到灯亮。
- **震动**：`termux-vibrate -d "$MILLISECONDS"` 或本机 `cmd vibrator_manager`；先读帮助。勿扰模式和系统强度设置可能影响效果；不默认使用强制忽略勿扰的参数。
- **红外遥控**：先查 `pm list features`、`termux-infrared-frequencies`。发射用 `termux-infrared-transmit -f "$HZ" "$PATTERN"`，频率和脉冲必须来自目标设备协议或用户提供的数据，检查单位与本机范围。发射接口可用不等于已获得遥控码；手机有发射器也不代表有红外接收学习能力。
- **NFC 标签**：查硬件、开关和 `termux-nfc` 本地 usage；按请求读取 NDEF，写入前明确标签和内容，写后重新读回。不能把 NFC 支持泛化为复制门禁卡、支付卡或任意受保护标签的能力。

## 传感器、定位与剪贴板

```sh
termux_api termux-sensor -l
termux_api termux-sensor -s "$SENSOR_NAME" -n 1
```

- 传感器名称从本机列表选取，不固定传感器数量或厂商名称。可包括加速度、陀螺仪、磁场、光照、距离、计步等；磁场数据不直接等于已经校准的方位角。
- 只读需要的传感器并限制次数；需要连续采样时明确频率和截止条件。清理只针对本次启动的采样，避免打断其他任务。
- `termux-location -p gps -r once` 获取本次位置；`last` 是缓存，不保证当前位置；`passive` 不主动请求更新。按用户需求选择，并检查时间、精度和 provider；不在自检中定位。
- `termux-clipboard-get` 读取剪贴板；文本通过 stdin 送给 `termux-clipboard-set`，避免插入 shell 源码。剪贴板可能有密码，不在无关任务中读取或完整回显。Android 前台限制可能阻止读取。

## 通知、对话框与通信

- **通知／Toast／对话框**：`termux-notification`、`termux-toast`、`termux-dialog`。指定独立通知 ID，避免覆盖其他通知；删除仅针对本次 ID。通知的 action／button 参数可执行命令，不能直接放未经校验的外部文本。
- **通知查看与暂缓**：`termux-notification-list` 或原生 `cmd notification` 的本机支持项。不要为读取通知自动授予 listener／assistant 权限；避免回显无关消息正文。
- **勿扰模式**：本机 `cmd notification set_dnd`。先记录旧设置并核对模式参数，不因通知测试默认关闭勿扰。
- **短信**：用已安装的 `termux-sms-list`／`termux-sms-inbox` 查询；发送用 `termux-sms-send -n "$NUMBER" -s "$SLOT"` 并从 stdin 提供正文。只按用户明确指定的接收者和内容发送；SIM slot 和发送结果分别核验，退出 0 不保证送达。
- **拨号**：`termux-telephony-call "$NUMBER"` 会发起电话；仅按明确拨号请求调用。只需展示号码时用拨号界面，不启动通话。
- **联系人／通话记录／蜂窝状态**：`termux-contact-list`、`termux-call-log`、`termux-telephony-cellinfo`、`termux-telephony-deviceinfo`。按任务读取必要字段，不把号码、设备标识、位置或通讯录写进项目。

## 壁纸、外观、电池与电源

- **壁纸**：`termux-wallpaper -f "$FILE"`；锁屏按本机支持的 `-l`。确认图片及目标屏幕，修改后查看；没有原图时不要承诺可完整恢复旧壁纸。
- **深色／夜间模式**：`cmd uimode help` 中的 night 参数，查询并记录原模式后修改。壁纸变暗、屏幕亮度和系统深色模式是不同功能。
- **电池／充电状态**：`dumpsys battery` 或 `termux-battery-status`；只读真实状态，不能用 `cmd battery set` 的模拟值作为测量结果。
- **省电、性能、游戏模式**：先查本机 `cmd power help`、`cmd game help` 及目标应用支持模式；按要求修改并验证，不在排障时默认强制性能或关闭温控。
- **亮屏／息屏、屏保**：本机 `cmd power wakeup/sleep`、`cmd dreams` 或明确的 `input keyevent`。亮屏不代表解锁；不要绕过锁屏认证。
- **保持唤醒**：`termux-wake-lock`／`termux-wake-unlock`，记录由本次任务取得的唤醒锁；仅需要持续任务时使用。
- **重启**：只在用户要求时执行，事先保留必要记录和重连方式。使用 `phone.py snapshot/compare` 核对 boot ID 和状态，不因网络断开直接认定重启成功。

## 文件访问、下载、分享与 USB 外设

- **选择／分享文件**：`termux-storage-get`、`termux-share`、`termux-open`，使用用户选定的文件和目标应用。调用分享界面不等于文件已经发送。
- **SAF 存储**：`termux-saf-*` 使用已有或用户授予的目录 URI，先查各子命令 usage。创建、读取、写入、重命名／删除仅在该工具实际支持且用户要求时执行；root 可访问路径不等于 Termux 获得了 SAF 授权。
- **下载／媒体扫描**：`termux-download`／`curl` 下载指定 URL，核对结果；`termux-media-scan` 将已确认文件交给媒体扫描，不递归扫描无关私人目录。
- **USB 外设访问**：`termux-usb -l` 列举；请求访问按其帮助处理授权及文件描述符。获得 USB FD 不等于拥有外设协议驱动。网卡专用操作见网络文档。
- 大文件传输和同步见 [远程与网络工具](remote-access.md)，不通过剪贴板搬运二进制文件。

## 定时任务、闹钟与指纹／密钥

- **计划脚本**：`termux-job-scheduler --pending` 查已有任务；按请求给出明确脚本路径、独立 job ID、网络条件与是否跨重启保留。脚本必须在 Termux 执行环境可访问，不能假定 chroot `/root` 路径可直接执行。
- `--period-ms` 是近似周期，当前安装版本提示周期任务最短 15 分钟；以本机帮助和系统约束为准，不承诺秒级准点。取消仅针对本次 job ID，不使用 `--cancel-all` 清理其他任务。
- **闹钟／倒计时**：解析本机能处理 `android.intent.action.SET_ALARM`／`SET_TIMER` 的应用，再按用户指定时间和时区通过其界面或 Intent 设置。核对应用里实际生成的项目，不把 JobScheduler 当作准点闹钟。
- **指纹认证**：`termux-fingerprint` 发起系统认证，检查成功、失败或取消结果；它不是读取指纹模板或解锁任意设备的工具。
- **Android Keystore**：先查看 `termux-keystore` 本机帮助。按用户指定 alias 生成、签名、验签或删除，核验结果；不覆盖／删除已有密钥来测试，不导出或输出秘密材料。
