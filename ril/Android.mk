LOCAL_PATH := $(call my-dir)

# Samsung CAF rild (hardware/ril-caf) needs libril_shim to interpose
# android::Parcel::writeString16 for the prebuilt libsec-ril.so
include $(CLEAR_VARS)

LOCAL_SHARED_LIBRARIES := liblog libcutils libbinder libutils
LOCAL_SRC_FILES := ril_shim.c
LOCAL_MODULE := libril_shim
LOCAL_MODULE_CLASS := SHARED_LIBRARIES

include $(BUILD_SHARED_LIBRARY)
