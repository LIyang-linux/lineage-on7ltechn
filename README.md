# Galaxy On7 国行 (SM-G6000) 非官方 ROM 构建

在 GitHub Actions 免费 runner（4 vCPU / 16 GB，public 仓库不限时长）上，
从源码全自动编译 **三星 Galaxy On7 国行 SM-G6000（`on7ltechn`）** 的多个第三方 ROM。

- 设备：Samsung Galaxy On7 (CHN) SM-G6000
- SoC：MSM8916（Cortex-A53 ×4 @1.2GHz），Adreno 306，1.5 GB / 2.0GB RAM
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
| LineageOS 14.1 (Android 7.1.2) | `build-14.1.yml` | 🔧 **单卡可用**；**VoLTE 移植中**（modem 侧已通，框架已能编译；双卡已确认是原厂硬件限制） |

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
   - 成功：`lineage-*.zip` + `recovery.img`
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
| 设备树 `SIM_COUNT := 2`，7.1 的 `libril` 编成多卡后 rild 连不上 `rild2`，每 4 秒崩溃 | **改名原厂服务为 `ril-daemon2`**（对齐 `class_main.sh`）并保留 `libsec-ril-dsds.so` |
| `init_msm8916.cpp` 写死 `dsds`，空卡槽报 `NOT_READY` 导致 siminfo 不写入、IMEI 重复 | **framework 补丁**：`SubscriptionInfoUpdater` 把 `NOT_READY` 视同 `ABSENT` |
| `-DRIL_FIX_SMS_NOT_SENT_ERR` 是 8.1 才有的宏，7.1 telephony 无引用点（空操作） | 记录在案；若短信仍报错需自行移植对应逻辑 |

### GPU 超频说明（看芯片体质，别一概而论）

国行原厂 DTB 的 Adreno 306 频率表为 **400 / 310 / 200 / 19.2 MHz**。

- 650 MHz 并非必然崩溃：社区里不少 8916 机器能稳定跑 650，也有机器一超就出现
  **相机 / 浏览器 / TF 卡 / 亮屏崩溃**，甚至开机 logo 循环。**能否超取决于这颗
  SoC 的体质（漏电特性）**，同一型号不同批次都可能不一样。
- 建议按 400 → 550 → 650 逐档测试，每档至少跑一轮相机、浏览器、亮屏、TF 卡读写，
  稳定再往上。出现任何异常立刻降档。
- 本仓库的 boot 默认保持原厂 400 MHz（保证任何人刷入都能开机），超频请自行改 DTB。

### 14.1 双卡（结论：**原厂硬件就是单 4G + 副 2G，已放弃双卡目标**）

我们曾尝试把这台机器做成双卡双待，最终通过**逆向原厂 boot ramdisk**（`init.rilchip.rc`、
`init.class_main.sh`、`default.prop`）拿到了三星的完整配方：

| 项 | 原厂值 |
|---|---|
| RIL 服务 | `ril-daemon`（无 `-c`）+ `ril-daemon1`（`-c 2`，走 `rild.libpath2`） |
| 第二个 daemon 何时起 | `persist.radio.multisim.config=dsds/dsda` 或 `ro.multisim.simslotcount=2` |
| 库 | `rild.libpath=libsec-ril.so` / `rild.libpath2=libsec-ril-dsds.so` |
| **`ro.telephony.default_network`** | **`9,1`** ← slot0=LTE/GSM/WCDMA，**slot1=GSM only** |

**关键结论**：原厂对副卡的定位就是 **只能 2G**（早期 CMCC DSDS = 主卡 4G + 副卡 2G 语音），
而当地移动 2G 已经退网 —— 所以"副卡通不了网"是**设计如此**，不是没修好。
（另外 cm-14.1 的 msm8916-common 把服务命名为 `ril-daemon1`，但 `class_main.sh` 要
`start ril-daemon2`，名字对不上会导致第二个守护进程从不启动；这个坑我们踩过并记录在 workflow 里。）

因此本项目**回到单卡稳定配置**（`SIM_COUNT := 1` + 双 RIL 服务），把精力转向 VoLTE。

> 验收标准（历史）：两个卡槽各插一次 SIM 都能识别 —— 这一条曾经达到过。

## 已知问题

- **VoLTE 未通**：移动 4G 下打电话走 CSFB 回落 2G/3G（能打通，但不是 VoLTE）。移植进行中（见下节）
- **双卡不做**：逆向原厂固件确认副卡被限制为 GSM only（`ro.telephony.default_network=9,1`），而当地移动 2G 已退网 → 副卡必然无服务。项目回归**单卡稳定配置**
- **IMS 框架已能编译进 ROM**：`android.telephony.ims.*`（Android 9 版）+ 旧 `ims-common`/`telephony-common` 适配完成；但 ROM 里还**没有 IMS 服务端 apk**，所以打电话仍不走 VoLTE
- **短信可能显示发送失败**：实际已送达但框架判定失败，`RIL_FIX_SMS_NOT_SENT_ERR` 在 7.1 无效
- **RAM 1.5 GB / 2.0 GB 两个版本**：8.1 上多任务容易杀后台，7.1.2 明显更轻
- **相机**：部分场景（HDR、闪光灯）可能异常，取决于 blobs 版本

## 未完成 / 以后做

以下事项**尚未完成**，留作后续方向，任何感兴趣的人可以按这里的结论接着做。

### 1. VoLTE（状态：**移植进行中**，方案见 `docs/volte-port-steps.md`）

**已查清的事实（2026-11 更新）：**

| 层 | 现状 |
|---|---|
| **modem** | **支持**：实测 `ril.ims.ltevoicesupport=1`、RILD 上报 `VoPS=1`（硬件/固件都 OK） |
| **移动配置** | 原厂 modem 只有 CSFB；但高通官方 carrier 配置 **`china/cmcc/csfb/dsds/volte_co/mcfg_sw.mbn`**（标识 `CMCC_C_DS_VC`）现成可用 |
| **AP 侧 IMS** | 原厂 5.1.1 有组件（`imscmservice` + `lib-ims*.so` + jars），但缺 `imsservice.apk`；**Android 7.1 完全没有 `android.telephony.ims.*`**（该包是 9.0 引入的新 IMS 架构） |
| **可用 apk** | `com.sec.imsservice` 找到**骁龙版**（SM8250），依赖的 `ims-common`/`imsmanager`/`telephony-common`/`rcsopenapi` **原厂固件全有** |

**关键结论**：障碍不在 modem，而在 **7.1 缺整套 Android 9 IMS 框架**。项目路线见
[`docs/volte-port-steps.md`](docs/volte-port-steps.md)（20 步：补框架 → 适配 apk → 注入 modem 配置）。

当前进度：**阶段 B 收尾（框架已能整体编译通过）**，正在往阶段 C/D 走。

- ✅ modem 侧：`volte_co` mcfg 注入并真机验证（开机/短信/4G 正常，`ril.ims.ltevoicesupport=1`）
- ✅ framework：`android.telephony.ims.*` 68 个文件注入 `frameworks/base`，编译通过
- ✅ `ims-common`（旧库）+ `telephony-common`（ImsPhone 栈）适配 9.0 接口，编译通过
- ⏳ 待做：阶段 C 框架方法补丁、阶段 D 三星 IMS apk 打包/签名/SELinux、阶段 E 真机注册与通话

> **阶段 D 的真实缺口（2026-11-26 清点）**：不是"放个 apk 进去"那么简单。
> 平台侧负责"发现并绑定 IMS 服务"的胶水类 **`ImsResolver` / `ImsManager`(9.0) /
> `ImsServiceController` 都不存在**（7.1 只有旧 `com.android.ims.ImsManager`）。
> 有两条路：① 移植这三个类（工程量大，且要处理 SDK25 缺失 API）；
> ② 先看三星 apk 能否直接挂在**旧链路**上（它同时实现了 `com.android.ims.internal.*`），
> 这条更快但未必走得通 —— 下一步就是拿 apk 实测。

> 最近一次构建 run `45639200715`（2026-11-26）：单卡配置（`SIM_COUNT=1` + 双 RIL 服务）。

> 另一条备选路线：直接在 **15.1（8.1）** 上做（8.1 已有 `ImsService` 框架），上层障碍少很多。

搜索结论：GitHub 上**没有** SM-G6000 / Galaxy On7 的 VoLTE 移植成果；本项目是第一次尝试。

### 2. 短信发送状态误报（状态：未完成）

现象：短信实际已送达，手机仍显示"未发送"。`BoardConfig.mk` 里的
`-DRIL_FIX_SMS_NOT_SENT_ERR` 是 8.1 才存在的宏，7.1 的 `frameworks/opt/telephony`
中没有任何引用点，等于空操作。修法是把这个宏对应的应答判别逻辑补进 7.1 的 `RIL.java`。

### 3. 内核优化（部分完成）

只做收益明确、风险低的四项，其余（1.8GHz、关 FSync、SELinux permissive、-O3）不做：

- `CONFIG_WQ_POWER_EFFICIENT_DEFAULT=y`（省电）
- Adreno Idler / simple_ondemand（GPU 空闲降频）
- Touch Boost（响应）
- zram 512MB + lz4（2GB 机型的多任务收益大于超频）

## 许可证

本仓库（设备树、workflow、补丁脚本）采用 **GPL-2.0**，与内核保持一致，保证任何人拿走后
都要把修改放回公开渠道。

需要说明适用范围：

| 内容 | 许可证 |
|---|---|
| 本仓库的设备树 / workflow / 脚本 | GPL-2.0 |
| 内核源码（Galaxy-MSM8916 仓库） | GPL-2.0 |
| LineageOS 系统代码 | Apache-2.0（部分 GPL） |
| 三星原厂 blobs（vendor/samsung） | 无开源许可，版权归三星，仅随 ROM 分发，不在本协议范围内 |

三者可以共存：Apache-2.0 代码可以并入 GPL-2.0 项目，反之不行。所以把整个仓库定成
GPL-2.0 在法务上是安全的，只是会让下游无法只用 Apache-2.0 的条款取用设备树部分。

## 致谢

### 系统与设备

| 项目 | 用途 |
|---|---|
| [Galaxy-MSM8916](https://github.com/Galaxy-MSM8916) | msm8916 全套设备树、vendor blobs、内核（本项目的硬件基础） |
| [LineageOS](https://github.com/LineageOS) | 系统源码（14.1 / 15.1） |
| [creeperxyz86/releases_o7prolte](https://github.com/creeperxyz86/releases_o7prolte) | 国际版 17.1 移植，本项目的起点 |
| [AOSP](https://android.googlesource.com/platform/frameworks/base/) | `android.telephony.ims.*` 等框架源码（VoLTE 阶段移植来源） |

### VoLTE / IMS（本项目参考的关键成果）

| 项目 | 用途 |
|---|---|
| [akbar-npj/msm8916-openwrt](https://github.com/akbar-npj/msm8916-openwrt) | **中国移动 VoLTE modem 配置**（`qcom-carrier-autocfg` 的 `cmcc/.../volte_co`）+ msm8916 VoLTE 启用 SOP |
| [SolidEva/sm8250-samsung-imsservice-apk](https://github.com/SolidEva/sm8250-samsung-imsservice-apk) | **骁龙版三星 IMS apk**（`com.sec.imsservice`，含 smali/res），VoLTE 的服务端 |
| [WeWaffles/OneLineage](https://github.com/WeWaffles/OneLineage) | **在 AOSP/LineageOS 上运行三星 IMS 的完整方法**与补丁工具（`docs/SAMSUNG_IMS.md`） |
| [fahadalijaved/OneOS](https://github.com/fahadalijaved/OneOS) | 上述补丁的源头（Apache-2.0），桩实现思路 |
| [jameskdev/android_samsung_imsservice](https://github.com/jameskdev/android_samsung_imsservice) | 三星 IMS 适配 AOSP compat 接口的参考 |
| [xyls985/msm8916-volte-sms](https://github.com/xyls985/msm8916-volte-sms) | msm8916 平台 IMS（SMS over IMS）协议实现参考，验证了 modem 侧可行 |

### 同一台机器的其他项目

| 项目 | 用途 |
|---|---|
| [pmos-on7ltechn](https://github.com/LIyang-linux/pmos-on7ltechn) | 同机型的 postmarketOS 移植（触摸/显示/GPU/充电等硬件逆向成果） |

### 其他

- XDA / 社区里所有 8916 机型的 VoLTE 讨论（超频体质、IMS 行为）
- 以及当年花 29 块把它从闲鱼捞出来的自己 🫡
