/*
 * Copyright (C) 2013 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.android.ims.internal;

import android.os.Bundle;

/**
 * 三星私有 IMS 回调接口。
 *
 * AOSP 没有这个类型，SM8250 的 imsservice.apk（Android 10）通过它接收来电和
 * CDPN（Called Party Number）信息。这里按 apk 里实际的 invoke-interface 签名补齐：
 * <ul>
 *   <li>{@code onIncomingCall(int, Bundle)}</li>
 *   <li>{@code onCdpnInfo(String, int)}</li>
 * </ul>
 *
 * @hide
 */
public interface ISecImsMmTelEventListener {

    /** 收到一路 IMS 来电。 */
    void onIncomingCall(int callId, Bundle extras);

    /** 收到对端号码（CDPN）信息。 */
    void onCdpnInfo(String number, int callId);
}
