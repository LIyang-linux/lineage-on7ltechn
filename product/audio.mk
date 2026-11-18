# Permissions
PRODUCT_COPY_FILES += \
	frameworks/native/data/etc/android.hardware.audio.low_latency.xml:system/etc/permissions/android.hardware.audio.low_latency.xml

# 7.1 的 audioserver 必须显式打包（否则 AudioFlinger/APS 都不存在）
PRODUCT_PACKAGES += \
	audioserver
