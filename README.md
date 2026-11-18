# LineageOS for Galaxy On7 国行 (SM-G6000) — GitHub Actions 云编译

在 GitHub Actions 的免费 runner（4 vCPU / 16 GB，public 仓库不限时长）上，
从源码全自动编译 **三星 Galaxy On7 国行 SM-G6000（代号 `on7ltechn`）** 的
非官方 LineageOS 刷机包。

- 设备：Samsung Galaxy On7 (CHN) SM-G6000
- SoC：MSM8916 (Cortex-A53 ×4 @1.2GHz)，Adreno 306，2 GB RAM
- 屏幕：720×1280，触摸控制器 ZT7548
- 摄像头：后置 S5K3L2XX，前置 S5K5E3YX
- Bootloader：G6000ZCS2BRI1
- **system 分区实测 1,828,716,544 字节（1744 MB）**，设备树默认值 2 GB 写不进去，本仓库已修正

## 仓库结构

| 分支 / 路径 | 内容 |
|---|---|
| `main` | 两条 GitHub Actions workflow + 本 README |
| `cm-14.1-o7-common` | o7-common 设备树（LineageOS 14.1 用，从 15.1 回移） |
| `cm-14.1-on7ltechn` | on7ltechn 机型树（LineageOS 14.1 用，从 15.1 回移） |
| `.github/workflows/build.yml` | **LineageOS 15.1 (Android 8.1)** 编译流水线 |
| `.github/workflows/build-14.1.yml` | **LineageOS 14.1 (Android 7.1.2)** 编译流水线 |

15.1 的设备树 / vendor / 内核直接取自
[Galaxy-MSM8916](https://github.com/Galaxy-MSM8916) 组织的 `lineage-15.1` 分支；
14.1 的公共部分取自该组织与 LineageOS 的 `cm-14.1` 分支，o7 机型部分用本仓库的回移分支。

## 怎么用

1. 仓库页 → **Actions** → 选择对应 workflow
   （`Build LineageOS 15.1` / `Build LineageOS 14.1`）
2. **Run workflow** → 等待约 2–2.5 小时
3. 本次 run 页面底部 **Artifacts** 下载：
   - 成功：`lineage-15.1-*-UNOFFICIAL-on7ltechn.zip`（或 14.1 对应产物）
   - 失败：`build-log`（贴 issue 继续修）

注意：artifact 需要**登录 GitHub** 才能下载，且 90 天过期。长期保存请自行转存。

### 刷入（TWRP）

1. 刷 ROM zip：Wipe → Advanced → 勾选 System / Cache / Dalvik / Data → Install
2. 首次从其他系统切换建议 **Format Data**（加密布局不同）
3. 不含 GApps；系统自带 WebView，国内使用无需谷歌套件

## 编译环境与已修问题清单

宿主是 ubuntu-22.04 runner，源码为 `repo init --depth=1` 浅克隆。
以下问题都在 workflow 内自动修补，供后人参考：

### LineageOS 15.1（build.yml）

| 问题 | 修法 |
|---|---|
| runner 磁盘只有 ~14 GB，同步+编译放不下 | `easimon/maximize-build-space` 扩容到 /mnt/build |
| 构建脚本为 Python 2 语法 | apt 装 python2，软链到 `/usr/local/bin/python` |
| audio HAL（Galaxy-MSM8916 fork）混入 Android 9 的 `AudioPolicyMix` 写法 | 改回 15.1 官方写法（`mPolicyMix.promote()`） |
| 15.1 内核分支缺国行 defconfig `msm8916_sec_o7lte_chnopen_defconfig` | 从 17.1 分支拷贝（Kconfig 的 `MACH_O7_CHN_OPEN` 已存在） |
| GCC ≥10 默认 `-fno-common`，3.10 内核宿主工具 dtc 链接报 `yylloc multiple definition` | 内核顶层 Makefile 的 `HOSTCFLAGS` 追加 `-fcommon` |
| Android 8.1 的 Jack 在新版 JDK8 上 SSL 握手失败 | `ANDROID_COMPILE_WITH_JACK := false`（走 javac + dx） |
| `external/chromium-webview` 的 `webview.apk` 是 133 字节 Git LFS 指针 | 用 LFS batch API 从 `review.lineageos.org` 拉真实文件（~90 MB） |
| 设备树按国际版生成 2 GB system 镜像，国行分区只有 1744 MB，刷入报 `lseek64 failed` / Error 7 | `BOARD_SYSTEMIMAGE_PARTITION_SIZE := 1828716544`（`blockdev --getsize64` 实测值） |

### LineageOS 14.1（build-14.1.yml）

| 问题 | 修法 |
|---|---|
| 上游无 o7 的 14.1 设备树 | 本仓库 `cm-14.1-o7-common` / `cm-14.1-on7ltechn` 两个回移分支 |
| cm-14.1 内核无国行 defconfig | 同上，从 17.1 分支拷贝 |
| vendor mk 按 8.1 写到 `/vendor`、`*.vendor.msm8916.so` 命名 | 同步时改写为 `/system` 路径与 7.1 命名（`camera.msm8916.so` 等） |
| Jack 时代同样的问题 | 同样 `ANDROID_COMPILE_WITH_JACK := false` |

### GPU 超频说明（重要）

国行原厂 DTB 的 Adreno 306 频率表为 **400 / 310 / 200 / 19.2 MHz** 四档。
三方移植版（安卓10.0）内核曾把上限提到 650 MHz，在实机上会引发**相机 / 浏览器 / TF 卡 / 亮屏崩溃**，
降回 400 MHz 后恢复正常。本仓库编译的 boot 默认保持原厂 400 MHz。
如需自行超频，改 DTB 中 `qcom,gpu-pwrlevels` 的频率值后重打 boot.img 即可，风险自负。

## 设备树来源与致谢

- [Galaxy-MSM8916](https://github.com/Galaxy-MSM8916) — msm8916 全家桶
  （设备树、vendor blobs、内核、audio HAL），本仓库的编译源头
- [LineageOS](https://github.com/LineageOS) — 系统源码
- [creeperxyz86/releases_o7prolte](https://github.com/creeperxyz86/releases_o7prolte) —
  国际版 o7prolte 的 17.1 移植，本项目最初的灵感来源

## 状态

| 目标版本 | 状态 |
|---|---|
| LineageOS 15.1 (8.1) | ✅ 可编译、可刷入（分区已修正） |
| LineageOS 14.1 (7.1.2) | 🚧 移植中（设备树已回移，首次构建进行时） |
| 更低版本 | ❌ 内核无 cm-13.0 分支，不可行 |
