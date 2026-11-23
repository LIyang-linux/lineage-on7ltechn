# 中国移动 VoLTE 魔改方案（on7ltechn / LineageOS 14.1，20 步）

> 目标：在 **Android 7.1** 上跑三星 IMS（SM8250 apk），实现移动 VoLTE。
> 策略：**补齐 Android 8.0 的 IMS 框架类** + 适配 apk + 注入 modem 配置。
> 风险原则：**可回退**（每步有备份/验证点）。

---

## 背景：为什么难

| 层 | 7.1（我们的） | SM8250 apk 需要 |
|---|---|---|
| IMS 接口 | `com.android.ims.internal.*` | `android.telephony.ims.*`（8.0+） |
| 关键类 | 无 `ImsSmsImplBase` / `ImsCallProfile` / `MmTelFeature` | 必需 |
| modem | ✅ VoPS=1（支持） | 需加载 volte_co 配置 |

**核心矛盾**：7.1 缺整个 8.0 IMS 框架 → 要么**造出来**，要么**降级 apk**。

---

## 20 步计划

### 阶段 A：调研与准备（1–5）

| # | 步骤 | 产物 | 风险 |
|---|---|---|---|
| 1 | **modem 配置确认**：备份 `/modemst1`、`/modemst2`；导出当前 mcfg 列表 | 备份文件 + mcfg 清单 | 零（只读+备份） |
| 2 | **volte_co 配置注入验证**：把 `CMCC_C_DS_VC` 的 mcfg 临时加载（NV `mcfg_config_force_load`），看 modem 是否接受 | 验证结论 | 低（可回退） |
| 3 | **依赖清点**：列出 SM8250 apk 的全部 `uses-library` 与 native 库，核对原厂固件 | 依赖清单 | 零 |
| 4 | **API 差异审计**：扫描 apk 引用的 `android.*` 类，标记 7.1 缺失的 | 缺失类清单 | 零 |
| 5 | **回退方案**：准备原版 modem 备份 + 可启动的旧 ROM | 回退包 | 零 |

### 阶段 B：补齐 8.0 IMS 框架（6–12）

| # | 步骤 | 内容 |
|---|---|---|
| 6 | **`android.telephony.ims.ImsReasonInfo`** | 7.1 缺失，需补（简单数据类） |
| 7 | **`android.telephony.ims.ImsCallProfile`** | 含 `setCallExtraStringArray` 等 |
| 8 | **`android.telephony.ims.ImsStreamMediaProfile` / `ImsConferenceState`** | 数据类 |
| 9 | **`android.telephony.ims.aidl.IImsCallSessionListener` / `IImsRegistration` / `IImsSmsListener`** | AIDL 接口（默认方法） |
| 10 | **`android.telephony.ims.stub.ImsSmsImplBase`** | SMS over IMS 基类（含五参数错误上报） |
| 11 | **`android.telephony.ims.feature.MmTelFeature` + `ImsFeature$Capabilities`** | 特性基类（`mContext` 改 protected） |
| 12 | **`android.telephony.ims.ImsSsInfo$Builder.setServiceClass`** | 补充方法 |

### 阶段 C：框架补丁（13–16）

| # | 步骤 | 内容 |
|---|---|---|
| 13 | **`ServiceState` 补丁** | 补 `isPsOnlyReg()`、`getSnapshotStatus()` |
| 14 | **`INetworkManagementService` 补丁** | 补 `getNetworkStatsVideoCall`、`start/stopNetworkStatsOnPorts` |
| 15 | **`UserHandle.SEM_CURRENT` / `IccUtils.getIccType`** | 静态别名 + 方法 |
| 16 | **`TelephonyManager` 三星方法** | `getGroupIdLevel2` 等（按缺失清单） |

### 阶段 D：APK 适配与打包（17–18）

| # | 步骤 | 内容 |
|---|---|---|
| 17 | **APK 适配** | 按缺失清单改 smali（`android.telephony.ims.*` → 我们的实现）；处理 `compileSdk=30` 的 API |
| 18 | **签名与权限** | 平台签名（`sharedUserId=android.uid.system`）；`etc/permissions/*.xml`；SELinux 策略 |

### 阶段 E：modem 与联调（19–20）

| # | 步骤 | 内容 |
|---|---|---|
| 19 | **modem 配置持久化** | 把 volte_co 写入 modem（或用 NV force_load 持久化）；重启验证 IMS 注册 |
| 20 | **真机验证** | `dumpsys ims` 注册状态 → 状态栏 HD → VoLTE 通话测试；异常回退 |

---

## 风险与回退

| 风险 | 回退 |
|---|---|
| 框架补丁导致系统不稳 | 保留原 `framework.jar`，可 fastboot 刷回 |
| modem 配置异常 | 还原 `/modemst1`、`/modemst2` 备份 |
| IMS 服务崩溃 | 卸载 apk / 禁用服务 |
| 变砖 | 原厂备份（`原厂备份/` 目录）+ TWRP |

---

## 关键参考

| 资源 | 用途 |
|---|---|
| `WeWaffles/OneLineage`（`docs/SAMSUNG_IMS.md`、`tools/patches/*`） | 三星 IMS 在 AOSP 的运行方法、补丁代码 |
| `fahadalijaved/OneOS`（Apache 2.0） | 补丁源头 |
| `SolidEva/sm8250-samsung-imsservice-apk` | 骁龙版 IMS apk |
| `jameskdev/android_samsung_imsservice` | 兼容层适配思路 |
| `xyls985/msm8916-volte-sms` | msm8916 IMS 协议参考 |
| `akbar-npj/msm8916-openwrt` | modem volte_co 配置 + VoLTE SOP |

---

## 进度

- [x] 阶段 0：调研（modem 支持确认、组件清点、接口差异）
- [ ] 阶段 A（1–5）
- [ ] 阶段 B（6–12）
- [ ] 阶段 C（13–16）
- [ ] 阶段 D（17–18）
- [ ] 阶段 E（19–20）

---

*最后更新：2026-11-23*
