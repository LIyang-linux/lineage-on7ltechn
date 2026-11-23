# 中国移动 VoLTE 移植方案（on7ltechn / LineageOS 14.1）

> 状态：**组件已凑齐，接口确认兼容；待做零风险验证**（2026-11-23 更新）
> 目标：让三星 Galaxy On7 国行（SM-G6000）在**中国移动**网络下使用 VoLTE 语音。

### 更新摘要（2026-11-23 深夜）

| 环节 | 结论 |
|---|---|
| ① modem VoLTE 配置 | ✅ 有现成（高通 `qcom-carrier-autocfg` 的 `china/cmcc/csfb/dsds/volte_co/mcfg_sw.mbn`，标识 `CMCC_C_DS_VC`，含移动 IMS 服务器 `xcap.ims.mnc000.mcc460`） |
| ② `imsservice.apk` | ✅ 找到**骁龙版**：`SolidEva/sm8250-samsung-imsservice-apk`（SM8250=骁龙865，含中国运营商 VoLTE 图标） |
| ③ 依赖 jar | ✅ **原厂固件全有**：`ims-common.jar`、`imsmanager.jar`、`telephony-common.jar`、`rcsopenapi.jar`、`commonimsinterface.jar`、`okhttp.jar` |
| ④ `IImsService` AIDL | ✅ **7.1 与 Android 10 方法签名一致**（`open/close/createCallSession/getUtInterface/getEcbmInterface/...`） |
| ⑤ apk 编译版本 | ⚠️ `compileSdk=30`（Android 11），需适配 7.1 API |
| ⑥ **零风险验证通道** | ✅ modem 支持 NV 项 `/nv/item_files/mcfg/mcfg_config_force_load` **强制加载 mcfg**（另有 `/nv/item_files/conf/mcfg.conf`）——**不用刷 modem 分区** |

---

## 1. 结论先行

| 问题 | 答案 |
|---|---|
| 原厂支持移动 VoLTE 吗？ | **不支持**（固件里移动只有 CSFB） |
| 能改出来吗？ | **有戏**——高通官方 carrier 配置里有现成的移动 VoLTE mcfg |
| 难度 | **高**（比双卡高一个量级），但不需从零逆向 |
| 是否值得 | 移动 4G 语音（否则走 CSFB 回落 2G/3G） |

---

## 2. 调研证据

### 2.1 原厂 modem 里没有移动 VoLTE

原厂备份 `modem.vfat.win`（TWRP 备份，tar 格式）解包后：

```
image/modem_pr/mcfg/configs/mcfg_sw/generic/china/
├── cmcc/          中国移动
│   ├── csfb/      → CMCC_C_DS_M / F1 / F2   （C = CSFB）
│   ├── 3csfb/     → CMCC_C_DS_F2 等
│   └── sglte/     → CMCC_S_DA_* / CMCC_S_SS_*
├── ct/            中国电信
│   └── svlte/     → 唯一可能的 VoLTE（SVLTE）
└── cu/            中国联通
    └── csfb/      → 无 VoLTE
```

**modem 镜像里还明确排除移动 IMS**：

```xml
<not> <imsi_plmn_in list="cmcc_plmns" /> </not>
stay in CSFB configuration with DSDS with RAT capability GWL
SGLTE NOT ENABLED
CSFB_ONLY! PLZ REBOOT
```

→ **原厂固件层面，移动被排除在 IMS/VoLTE 之外。**

### 2.2 但高通官方配置里有移动 VoLTE

`akbar-npj/msm8916-openwrt` 仓库的 `qcom-carrier-autocfg`：

```
packages/qcom-carrier-autocfg/files/mcfg/generic/china/cmcc/csfb/dsds/
├── comb_att/mcfg_sw.mbn
├── commerci/mcfg_sw.mbn
├── eps_only/mcfg_sw.mbn
├── lab_conf/mcfg_sw.mbn
├── lab_nsio/mcfg_sw.mbn
└── volte_co/mcfg_sw.mbn     ← 移动 VoLTE 配置
```

该文件（49888 bytes）的关键内容：

```
VOLTE_Commercial-CSFB-DSDS
CMCC_C_DS_VC                                  ← 移动双卡 VoLTE 标识
/nv/item_files/ims/qipcall_*                  ← IMS 语音（高通 qipcall）
/nv/item_files/modem/nas/lte_nas_ignore_mt_csfb_during_volte_call
/nv/item_files/modem/geran/grr/g2l_blind_redir_after_srvcc_control   ← SRVCC
xcap.ims.mnc000.mcc460.pub.3gppnetwork.org:80  ← 中国移动 IMS 服务器
simservs.ngn.etsi.org
```

**→ 移动的 VoLTE mcfg 是现成的，只是我们的 modem 没带。**

### 2.3 AP 侧 IMS 栈（原厂 5.1.1）

原厂 `system.ext4` 里有 IMS 组件：

```
bin/imscmservice          IMS 核心服务（高通）
bin/imsdatadaemon
bin/imsqmidaemon
bin/ims_rtp_daemon
etc/Diag_volte.cfg
etc/permissions/imscm.xml  → 引用 com.qti.ims.connectionmanager.imscmlibrary
framework/ims-common.jar
framework/imsmanager.jar
framework/commonimsinterface.jar
vendor/lib/lib-ims*.so      （13 个：lib-imss / lib-imsvt / lib-imsrcs / ...）
```

**缺口**：`imscmlibrary.jar` 缺失；init 里没有 IMS 服务定义；CSC 无 VoLTE 开关。

---

## 3. 方案

### 路线 A（推荐）：注入 modem VoLTE mcfg

modem 的 mcfg 是**按运营商选择的配置文件目录**，原厂设计就支持多配置。

**步骤**：

1. **提取**高通 `volte_co/mcfg_sw.mbn`（已下载到 `D:\DSH\mcfg\QUALCOMM_volte_co.mbn`）
2. **打包**进 modem 的 mcfg 目录（`/modem_pr/mcfg/configs/mcfg_sw/generic/china/cmcc/csfb/dsds/volte_co/`）
3. **重打包 modem 分区**（`modem.vfat.win` / `modem.img`），**先只读验证，不刷**
4. 验证 modem 是否接受该配置（AT 日志 / IMS 注册尝试）

**风险**：动 modem 分区，**有变砖风险**。原厂备份 `modem.vfat.win` 可恢复。

### 路线 B：AP 侧 IMS 移植（必须与 A 配合）

单靠 AP 侧不行——VoLTE **必须 modem 主动发起**（IMSD `0x20`），AP 无法代劳。

但 A 成功后仍需 AP 侧 IMS 栈：

1. 提取原厂 IMS 组件（`imscmservice` + `lib-ims*.so` + jars）
2. **补 `imscmlibrary.jar`**（缺失，可能要自己编或从其他固件找）
3. **适配 5.1.1 → 7.1 接口**（参考 `jameskdev/android_samsung_imsservice`）
4. 补 init 服务定义、权限、SELinux 策略
5. carrier config（移动）

---

## 4. 关键参考

| 资源 | 用途 |
|---|---|
| `akbar-npj/msm8916-openwrt` | 移动 VoLTE mcfg + msm8916 VoLTE SOP（`Docs/Modem Stability/220_VOLTE_ENABLEMENT_SOP.md`） |
| `jameskdev/android_samsung_imsservice` | 三星 IMS 服务（README 称骁龙也可能兼容 `libsec-ril` 接口） |
| `eErenYeager/ims_apk` | IMS APK |
| `myesxc/Samsung-s20-ims-compat-layer` | 三星 IMS 兼容层 |
| 原厂 `system.ext4` | IMS 组件来源 |
| 原厂 `modem.vfat.win` | modem 配置与备份 |

---

## 5. 风险与对策

| 风险 | 对策 |
|---|---|
| 刷 modem 变砖 | 保留 `modem.vfat.win` 备份；用 TWRP 可恢复 |
| modem 不认新 mcfg | 先只读验证；不行就回退 |
| IMS 接口不兼容（5.1 vs 7.1） | 参考 jameskdev 的兼容层 |
| SELinux 拦截 | 原厂有 `imscm.xml`；可能要 permissive 先测 |
| 移动网络侧限制 | 需实测；移动 4G VoLTE 需 IMS 注册成功 |

---

## 6. 验证清单

```bash
# 1. modem 是否加载 VoLTE 配置
adb logcat -b all | grep -iE "mcfg|volte|ims"

# 2. IMS 是否注册
adb shell dumpsys ims | grep -iE "registration|registered"
adb shell getprop | grep -iE "ims|volte"

# 3. 状态栏 HD / VoLTE 标识
# 4. 通话测试：拨号 → 是否保持 4G（不掉 2G/3G）
```

---

## 7. 时间线（暂定）

| 阶段 | 内容 |
|---|---|
| 1 | 只读验证 modem 是否接受 volte_co 配置 |
| 2 | 刷入 modem 配置，验证 IMS 注册 |
| 3 | 移植 IMS 栈到 7.1 |
| 4 | 真机 VoLTE 通话测试 |

**前置**：14.1 双卡版稳定（本方案与双卡共用 modem/RIL 链路，先保证双卡不回退）。

---

## 8. 零风险验证方案（最低风险优先）

**原则**：先不改手机任何持久化数据，用**可恢复**的手段验证。

### 8.1 modem 的免刷加载机制（关键发现）

modem 固件里存在：

```
/nv/item_files/mcfg/mcfg_config_force_load      ← 强制加载指定 mcfg
/nv/item_files/mcfg/mcfg_def_config_force_load
/nv/item_files/mcfg/mcfg_autoselect_by_uim      ← 按 UIM 自动选择
/nv/item_files/conf/mcfg.conf                   ← 文本配置
/dev/mcfg/sw_default_config
/dev/mcfg/hw_default_config
```

→ **可通过 NV 项临时强制加载 volte_co 配置，无需重刷 modem 分区。**

### 8.2 风险阶梯

| 阶段 | 操作 | 风险 | 恢复方式 |
|---|---|---|---|
| **0** | **纯只读**：`getprop`、`dmesg`、`logcat`、读 `/nv` | **零** | 无需恢复 |
| **1** | 备份 `/modemst1`、`/modemst2` 后写 NV `mcfg_config_force_load`，重启 modem | 低 | 还原备份 / 重启失效 |
| **2** | 持久化（写入 NV 或刷 modem 分区） | 中 | 用原厂 `modem.vfat.win` 恢复 |

### 8.3 阶段 0 检查清单（可立即执行）

```bash
# 1. modem/mcfg 相关属性
adb shell getprop | grep -iE 'mcfg|ims|volte|vowifi'

# 2. diag 设备（写 NV 需要）
adb shell ls -l /dev/diag* /dev/qmi*

# 3. modem 分区与 NV
adb shell ls /dev/block/bootdevice/by-name/ | grep -iE 'modem|efs'

# 4. 当前 IMS 状态
adb shell dumpsys ims 2>/dev/null | head -20
adb logcat -d | grep -iE 'ims|volte|mcfg' | tail -30
```

### 8.4 阶段 1（低风险）步骤

1. **备份**（必须）：
   ```bash
   adb shell "dd if=/dev/block/bootdevice/by-name/modemst1 of=/sdcard/modemst1.bak"
   adb shell "dd if=/dev/block/bootdevice/by-name/modemst2 of=/sdcard/modemst2.bak"
   ```
2. 放置 `volte_co/mcfg_sw.mbn` 到 modem 可读路径
3. 写 NV `mcfg_config_force_load`（值需查 modem 文档，通常为配置索引）
4. **重启 modem**（`setprop ctl.restart ril-daemon` 或重启手机）
5. 观察：`logcat` 里 modem 是否加载 volte_co、IMS 是否注册

**回退**：还原备份 或 重启（若未持久化）。

### 8.5 apk 适配（阶段 2+）

- SM8250 的 `GoogleImsService` 继承 `com.android.ims.internal.IImsService$Stub`（AOSP 标准）
- 7.1 的 `IImsService.aidl` 与 Android 10 **方法签名一致** → 接口层基本不用改
- 主要工作：
  1. 反编译 apk（仓库已提供 apktool 产物）
  2. 排查 Android 8+ API 调用（`compileSdk=30`）
  3. 补 `sharedUserId=android.uid.system` 的**平台签名**
  4. 配 SELinux 策略（原厂 `etc/permissions/imscm.xml` 可参考）
  5. 装依赖 jar（原厂已全有）

---

*最后更新：2026-11-23*
