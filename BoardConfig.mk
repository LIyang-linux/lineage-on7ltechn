# Inherit from common
include device/samsung/o7-common/BoardConfigCommon.mk

LOCAL_PATH := device/samsung/on7ltechn

# Asserts
TARGET_OTA_ASSERT_DEVICE := on7ltechn

# Kernel
TARGET_KERNEL_VARIANT_CONFIG :=  msm8916_sec_o7lte_chnopen_defconfig

# Partition sizes
BOARD_SYSTEMIMAGE_PARTITION_SIZE    := 1828716544
BOARD_USERDATAIMAGE_PARTITION_SIZE  := 5016350720

# RIL
SIM_COUNT := 2
BOARD_GLOBAL_CFLAGS += -DRIL_FIX_SMS_NOT_SENT_ERR

# Android 8+ 的 Jack 在新 JDK8 上会 SSL 握手失败，14.1 同样关闭
ANDROID_COMPILE_WITH_JACK := false
