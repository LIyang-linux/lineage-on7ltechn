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
| LineageOS 14.1 (Android 7.1.2) | `build-14.1.yml` | ✅ 可编译、可刷入；单卡（仅 SIM0） |

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
| 设备树 `SIM_COUNT := 2`，7.1 的 `libril` 编成多卡后 rild 连不上 `rild2`，每 4 秒崩溃 | 改为 `SIM_COUNT := 1`（见下节单卡限制） |
| `init_msm8916.cpp` 按 bootloader 卡槽数写死 `dsds`，导致订阅表为空、IMEI 重复 | 改 `dsds_properties()` 为单卡值 |
| `-DRIL_FIX_SMS_NOT_SENT_ERR` 是 8.1 才有的宏，7.1 telephony 无引用点（空操作） | 记录在案；若短信仍报错需自行移植对应逻辑 |

### GPU 超频说明（看芯片体质，别一概而论）

国行原厂 DTB 的 Adreno 306 频率表为 **400 / 310 / 200 / 19.2 MHz**。

- 650 MHz 并非必然崩溃：社区里不少 8916 机器能稳定跑 650，也有机器一超就出现
  **相机 / 浏览器 / TF 卡 / 亮屏崩溃**，甚至开机 logo 循环。**能否超取决于这颗
  SoC 的体质（漏电特性）**，同一型号不同批次都可能不一样。
- 建议按 400 → 550 → 650 逐档测试，每档至少跑一轮相机、浏览器、亮屏、TF 卡读写，
  稳定再往上。出现任何异常立刻降档。
- 本仓库的 boot 默认保持原厂 400 MHz（保证任何人刷入都能开机），超频请自行改 DTB。

### 7.1.2 单卡限制（已固化，不建议再改）

14.1 只支持 **SIM0**，这不是临时规避，而是三层一致后的结果：

| 层 | 改动 | 原因 |
|---|---|---|
| `libril`（C，最底层） | `SIM_COUNT := 1` | `=2` 时编入 `-DANDROID_SIM_COUNT_2`，rild 会去连 `rild2`，没有该 socket 就每 4 秒崩溃 |
| init | `persist.radio.multisim.config=none`、`ro.multisim.simslotcount=1` | 绕开 `init_msm8916.cpp` 的 `dsds_properties()` |
| framework | `system_prop.mk` 补 `multisim.config=none` | vendor / blob 里的默认值会盖掉 system 的，需显式覆盖 |

其中两个坑值得记录：

- **`dsds` 是 init 在 `/data` 挂载前就 `property_set` 的**，只存在内存不落盘。
  所以 `rm /data/property/persist.radio.multisim.config` 后重启仍然是 `dsds`，
  必须改 `init_msm8916.cpp` 或运行期 `setprop`（会触发 `stop ril-daemon; start ril-daemon`）。
- 属性保持 `dsds` 时，`SubscriptionInfoUpdater.isAllIccIdQueryDone()` 会一直等
  卡槽 1 的 ICCID，而空卡槽只报 `NOT_READY`（不是 `ABSENT`），于是 `siminfo` 永远为空，
  设置里显示无 SIM；同时 `PhoneFactory` 建两个 Phone 对象，导致两个 IMEI 相同。

## 已知问题

- **通话不可用**：国行 2G/3G 退网后，SM-G6000 不支持 VoLTE，插卡只能上网不能打电话
  （VoLTE 待办，见下方「未完成 / 以后做」）
- **14.1 仅单卡**：`SIM_COUNT=1`，只服务 SIM0，卡槽 2 在软件栈里不存在（原因见上节）
- **短信可能显示发送失败**：实际已送达但框架判定失败，`RIL_FIX_SMS_NOT_SENT_ERR` 在 7.1 无效
- **RAM 1.5 GB / 2.0 GB 两个版本**：8.1 上多任务容易杀后台，7.1.2 明显更轻
- **相机**：部分场景（HDR、闪光灯）可能异常，取决于 blobs 版本

## 未完成 / 以后做

以下事项**尚未完成**，留作后续方向，任何感兴趣的人可以按这里的结论接着做。

### 1. VoLTE（状态：未完成，待攻克）

已查清的事实：

| 层 | 现状 |
|---|---|
| modem 固件 | **支持**：`modem.vfat.win` 内含 `ims_qmi_registration_apps_service.c`、`ims_qmi_settings_service.c`、`ims_qmi_presence_service.c`、`ims_task.cpp` 等，说明高通 QMI IMS 协议栈完整 |
| vendor blobs（AP 侧） | **缺失**：只有通用的 `libqmi.so` / `libqmi_cci.so` / `libqmiservices.so`，扫描全部 2391 个文件、1806 个 `.so`，**不存在** `libqti-ims.so`、`libimsqmi*.so`、`libsecims*.so`，也没有 IMS APK |
| framework | **缺失**：7.1 没有 `ImsService`；三星的 SecIMS 与 TouchWiz 私有接口深度耦合，无法单独搬出 |
| carrier config | **缺失**：AOSP 的 `CarrierConfig` 无 CMCC 的 VoLTE 参数集与 `ims` APN |

整条链路：

```
应用 → IMS 框架(✘) → libqti-ims.so(✘) → libqmi_cci(✔) → QMI IMS 服务(✔) → modem IMS 栈(✔)
```

后续可尝试的方向（按可行性排序）：

1. 从同代 **msm8916 且带高通 IMS** 的机型（如 Jio 定制机 LYF / YU 系列）提取 `libqti-ims.so` 及其 QMI 依赖，验证 ABI 与 QMI 服务版本是否匹配本机 modem。
2. 在 7.1 上实现一个最小的 IMS 客户端（SIP 注册 + QMI IMS 请求），直接走 `libqmi_cci`，绕过框架层；工作量巨大，但技术上不依赖专有库。
3. 放弃 7.1，直接在 **15.1（8.1）** 上做：8.1 已有 `ImsService` 框架与 `qti-telephony-common`，缺的仍是 `libqti-ims.so`，但上层障碍少很多。
4. 补齐 CMCC 的 IMS APN 与 carrier config（前三条通了之后才有意义）。

搜索结论：GitHub 上**没有任何** SM-G6000 / Galaxy On7 / 三星 msm8916 的 VoLTE 移植成果；
同类成果（LYF、YU）全部基于高通 QMI IMS + Android 9/10，不能直接套用。

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

- [Galaxy-MSM8916](https://github.com/Galaxy-MSM8916) — msm8916 全套设备树、vendor、内核
- [LineageOS](https://github.com/LineageOS) — 系统源码
- [creeperxyz86/releases_o7prolte](https://github.com/creeperxyz86/releases_o7prolte) — 国际版 17.1 移植，本项目的起点
- 以及当年花 29 块把它从闲鱼捞出来的自己
