# Permissions
PRODUCT_COPY_FILES += \
	frameworks/native/data/etc/android.hardware.audio.low_latency.xml:system/etc/permissions/android.hardware.audio.low_latency.xml

# 7.1 的 audioserver 必须显式打包（否则 AudioFlinger/APS 都不存在）
PRODUCT_PACKAGES += \
	audioserver

# 14.1 的 audio HAL 从 /system/etc 读 mixer_paths.xml 与 audio_effects.conf。
# 原厂/8.1 把这两份放在 /vendor/etc，7.1 找不到就会静音。
PRODUCT_COPY_FILES += \
    $(LOCAL_PATH)/configs/audio/mixer_paths.xml:system/etc/mixer_paths.xml \
    $(LOCAL_PATH)/configs/audio/audio_effects.conf:system/etc/audio_effects.conf
