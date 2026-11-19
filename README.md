# Galaxy On7 国行 (SM-G6000) 非官方 ROM 构建

在 GitHub Actions 免费 runner（4 vCPU / 16 GB，public 仓库不限时长）上，
从源码全自动编译 **三星 Galaxy On7 国行 SM-G6000（`on7ltechn`）** 的多个第三方 ROM。

- 设备：Samsung Galaxy On7 (CHN) SM-G6000
- SoC：MSM8916（Cortex-A53 ×4 @1.2GHz），Adreno 306，1.5 GB RAM
- 屏幕：720×1280，触摸控制器 ZT7548
- 摄像头：后置 S5K3L2XX，前置 S5K5E3YX
- Bootloader：G6000ZCS2BRI1
- **system 分区实测 1,744 MB**（1,828,716,544 字节），设备树默认 2 GB 写不进去，本仓库已修正

> 这机器原厂停在 Android 5.1.1，官方早已停止维护。本仓库的目标是让它跑上更新的系统，
> 并且把每一个踩过的坑都留在 workflow 里，任何人 fork 后点一下就能复现。

## 支持的系统

| 目标版本 | workflow | 状态 |
|---|---|---|
| LineageOS 15.1 (Android 8.1) | `build.yml` | ✅ 可编译、可刷入、日常可用 |
| LineageOS 14.1 (Android 7.1.2) | `build-14.1.yml` | 🚧 可点亮；暂无基带 |
| Resurrection Remix 5.8.5 (Android 7.1.2) | `build-rr.yml` | 🚧 首次构建进行中 |

> 7.1.2 是 LineageOS 的版本起点（LineageOS 由 CM14.1 接续而来），更低版本只能找
> CyanogenMod 12.1 / 13 的归档分支，那些源码树已无人维护，反而更难编译。

## 仓库结构

| 分支 / 路径 | 内容 |
|---|---|
| `main` | 三条 GitHub Actions workflow + 本 README |
| `cm-14.1-o7-common` | o7-common 设备树（7.1.2 用，从 8.1 回移） |
| `cm-14.1-on7ltechn` | on7ltechn 机型树（7.1.2 用，从 8.1 回移） |

公共部分（msm8916-common、vendor blobs、内核）取自
[Galaxy-MSM8916](https://github.com/Galaxy-MSM8916) 与 [LineageOS](https://github.com/LineageOS)。

## 怎么用

1. 打开 **Actions**，选择对应 workflow
2. **Run workflow**，等待约 2–3 小时
3. 在 run 页面底部 **Artifacts** 下载：
   - 成功：`lineage-*.zip` / `ResurrectionRemix-*.zip` + `recovery.img`
   - 失败：`build-log-*`（里面是完整编译日志）

artifact 需要登录 GitHub 才能下载，90 天后过期，长期保存请自行转存。

### 刷入（TWRP）

1. 备份 `boot`、`efs`、`modemst1/2`（EFS 丢了就没信号）
2. Wipe → Advanced → 勾选 System / Cache / Dalvik / Data
3. 跨大版本（8.1 ↔ 7.1.2）必须 **Format Data**（加密布局不同，否则卡开机动画）
4. 刷入 ROM zip，首次开机 5–10 分钟
5. 不含 GApps；系统自带 WebView，国内使用无需谷歌套件

## 已修问题清单

所有修补都写在 workflow 里，不需要手动打补丁。

### 通用

| 问题 | 修法 |
|---|---|
| runner 磁盘只有 ~14 GB | `easimon/maximize-build-space` 扩容到 `/mnt/build` |
| GCC ≥10 默认 `-fno-common`，3.10 内核宿主工具 dtc 报 `yylloc multiple definition` | 内核顶层 `HOSTCFLAGS` 追加 `-fcommon` |
| 内核缺国行 defconfig `msm8916_sec_o7lte_chnopen_defconfig` | 从 17.1 分支拷贝，走 `VARIANT_DEFCONFIG` 合并 |
| 设备树按 2 GB 生成 system 镜像，刷入报 `lseek64 failed` / Error 7 | `BOARD_SYSTEMIMAGE_PARTITION_SIZE := 1828716544` |

### LineageOS 15.1

| 问题 | 修法 |
|---|---|
| 构建脚本为 Python 2 语法 | 装 python2 并软链到 `/usr/local/bin/python` |
| audio HAL fork 混入 Android 9 的 `AudioPolicyMix` 写法 | 改回 15.1 写法 |
| 8.1 的 Jack 在新 JDK8 上 SSL 握手失败 | `ANDROID_COMPILE_WITH_JACK := false` |
| `external/chromium-webview` 的 `webview.apk` 是 Git LFS 指针 | 用 LFS batch API 拉真实文件 |

### LineageOS 14.1

| 问题 | 修法 |
|---|---|
| 上游无 o7 的 14.1 设备树 | 本仓库两个 `cm-14.1-*` 回移分支 |
| vendor mk 按 8.1 写到 `/vendor`、`*.vendor.msm8916.so` 命名 | 同步时改写为 `/system` 路径与 7.1 命名 |
| 各仓库自带 `ril.h` 比 AOSP 旧，缺 `MAX_SOCKET_NAME_LENGTH` | 编译前统一补齐 |
| `rild` 启动报 `library "libril_shim.so" not found` | 把 `msm8916-common/shim` 的模块加入 `PRODUCT_PACKAGES` |
| 7.1 的音频 HAL 从 `/system/etc/mixer_paths.xml` 读通路，包内缺失导致完全无声 | 从 17.1 包中提取本机验证过的配置拷入 `/system/etc` |

### GPU 超频说明（重要）

国行原厂 DTB 的 Adreno 306 频率表为 **400 / 310 / 200 / 19.2 MHz**。
三方移植内核曾把上限提到 650 MHz，实机会出现**相机 / 浏览器 / TF 卡 / 亮屏崩溃**，
降回 400 MHz 后恢复正常。本仓库的 boot 默认保持原厂 400 MHz，如需超频请自行改 DTB。

## 已知问题

- **通话不可用**：国行 2G/3G 退网后，SM-G6000 不支持 VoLTE，插卡只能上网不能打电话
- **RAM 仅 1.5 GB**：8.1 上多任务容易杀后台，7.1.2 明显更轻
- **相机**：部分场景（HDR、闪光灯）可能异常，取决于 blobs 版本

## 许可证

本仓库（设备树、workflow、补丁脚本）采用 **GPL-2.0**，与内核保持一致，保证任何人拿走后
都要把修改放回公开渠道。

需要说明适用范围：

| 内容 | 许可证 |
|---|---|
| 本仓库的设备树 / workflow / 脚本 | GPL-2.0 |
| 内核源码（Galaxy-MSM8916 仓库） | GPL-2.0 |
| LineageOS / RR 系统代码 | Apache-2.0（部分 GPL） |
| 三星原厂 blobs（vendor/samsung） | 无开源许可，版权归三星，仅随 ROM 分发，不在本协议范围内 |

三者可以共存：Apache-2.0 代码可以并入 GPL-2.0 项目，反之不行。所以把整个仓库定成
GPL-2.0 在法务上是安全的，只是会让下游无法只用 Apache-2.0 的条款取用设备树部分。

## 致谢

- [Galaxy-MSM8916](https://github.com/Galaxy-MSM8916) — msm8916 全套设备树、vendor、内核
- [LineageOS](https://github.com/LineageOS) / [ResurrectionRemix](https://github.com/ResurrectionRemix) — 系统源码
- [creeperxyz86/releases_o7prolte](https://github.com/creeperxyz86/releases_o7prolte) — 国际版 17.1 移植，本项目的起点
- 以及当年花 29 块把它从闲鱼捞出来的自己
