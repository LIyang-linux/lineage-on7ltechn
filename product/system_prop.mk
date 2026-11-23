# Radio
PRODUCT_DEFAULT_PROPERTY_OVERRIDES += \
	persist.radio.apm_sim_not_pwdn=1 \
	persist.radio.add_power_save=1

# Screen
PRODUCT_PROPERTY_OVERRIDES += \
	ro.sf.lcd_density=320

# Volume
PRODUCT_PROPERTY_OVERRIDES += \
	ro.config.vc_call_vol_steps=15 \
	ro.config.media_vol_steps=30

# Radio：双卡配置（DSDS）
# 之前这里是 none（单卡），原因是：
#   卡槽1 空时 sec-ril 只上报 NOT_READY（而非 ABSENT），
#   SubscriptionInfoUpdater.isAllIccIdQueryDone() 会一直等第二个 ICCID，
#   导致 siminfo 不写入、设置里显示无 SIM。
# 现在恢复 dsds —— 第二步会修 framework 让它容忍空卡槽。
# 注意：persist.* 属性若已存在于 /data/property，会覆盖这里的默认值，
# 刷机后需删除 /data/property/persist.radio.multisim.config 才会生效。
PRODUCT_PROPERTY_OVERRIDES += \
	persist.radio.multisim.config=dsds
