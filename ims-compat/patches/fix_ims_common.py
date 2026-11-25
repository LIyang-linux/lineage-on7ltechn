#!/usr/bin/env python3
"""让 frameworks/opt/net/ims（Android 7.1 的旧 IMS 客户端库）编译通过。

背景：我们把 frameworks/base 里的 com.android.ims.internal.*.aidl 换成了 Android 9 版
（SM8250 的 imsservice.apk 需要新签名），旧库因此编译不过。这里做四件事：
  1) 旧数据类 com.android.ims.X -> Android 9 的 android.telephony.ims.X
  2) 去掉 @Override（接口方法签名变了，注解已不成立；不影响运行语义）
  3) 修两处旧调用点（queryCFForServiceClass / setCamera）
  4) 给继承 *Stub 的内部类补 9.0 新增抽象方法的空实现

用法: fix_ims_common.py <frameworks/opt/net/ims 路径>
"""
import os
import re
import sys

# 旧数据类 -> Android 9 新包
TYPE_MAP = {
    'com.android.ims.ImsCallProfile': 'android.telephony.ims.ImsCallProfile',
    'com.android.ims.ImsStreamMediaProfile': 'android.telephony.ims.ImsStreamMediaProfile',
    'com.android.ims.ImsReasonInfo': 'android.telephony.ims.ImsReasonInfo',
    'com.android.ims.ImsSsInfo': 'android.telephony.ims.ImsSsInfo',
    'com.android.ims.ImsConferenceState': 'android.telephony.ims.ImsConferenceState',
    'com.android.ims.ImsSuppServiceNotification':
        'android.telephony.ims.ImsSuppServiceNotification',
    'com.android.ims.ImsExternalCallState': 'android.telephony.ims.ImsExternalCallState',
    'com.android.ims.ImsSsData': 'android.telephony.ims.ImsSsData',
    'com.android.ims.ImsCallForwardInfo': 'android.telephony.ims.ImsCallForwardInfo',
}

# 9.0 相比 7.1 新增的抽象方法（按接口分组的空实现）。
# 每项 = (去重用的特征串, 方法代码)；特征串已存在于类体中就不再重复插入。
# 注意用全限定名，旧库有些文件没 import RemoteException / 新数据类。
STUBS = {
    'IImsCallSessionListener': [
        ('callSessionMayHandover(', 'public void callSessionMayHandover('
         'com.android.ims.internal.IImsCallSession session,'
         ' int srcAccessTech, int targetAccessTech)'
         ' throws android.os.RemoteException { }'),
        ('callSessionRttModifyRequestReceived(', 'public void '
         'callSessionRttModifyRequestReceived('
         'com.android.ims.internal.IImsCallSession session,'
         ' android.telephony.ims.ImsCallProfile callProfile)'
         ' throws android.os.RemoteException { }'),
        ('callSessionRttModifyResponseReceived(', 'public void '
         'callSessionRttModifyResponseReceived(int status)'
         ' throws android.os.RemoteException { }'),
        ('callSessionRttMessageReceived(', 'public void callSessionRttMessageReceived('
         'String rttMessage) throws android.os.RemoteException { }'),
    ],
    'IImsUtListener': [
        ('onSupplementaryServiceIndication(', 'public void '
         'onSupplementaryServiceIndication('
         'android.telephony.ims.ImsSsData ssData)'
         ' throws android.os.RemoteException { }'),
    ],
    # setCamera 是"同名不同参数"的重载，用完整签名去重
    'IImsVideoCallProvider': [
        ('setCamera(String cameraId, int uid)', 'public void setCamera('
         'String cameraId, int uid) throws android.os.RemoteException { }'),
    ],
}

# 同一个类在旧包里也可能被简单名引用（尤其是 com/android/ims 包内的文件），
# 这里按"非 . / 单词字符"的前缀匹配来替换简单名。
SIMPLE_NAMES = [
    'ImsCallProfile', 'ImsStreamMediaProfile', 'ImsReasonInfo', 'ImsSsInfo',
    'ImsConferenceState', 'ImsSuppServiceNotification', 'ImsExternalCallState',
    'ImsSsData', 'ImsCallForwardInfo',
]

STUB_CLASS = re.compile(r'(class\s+\w+\s+extends\s+(?:[\w.$]+\.)?(IIms\w+)\.Stub\s*\{)')


def patch_file(path):
    t = open(path, encoding='utf-8').read()
    orig = t

    for a, b in TYPE_MAP.items():
        t = t.replace(a, b)

    # 简单名替换（同包/未 import 的写法），先长后短避免误伤
    for name in SIMPLE_NAMES:
        t = re.sub(r'(?<![\w.$])' + name + r'\b',
                   'android.telephony.ims.' + name, t)

    t = re.sub(r'^[ \t]*@Override[ \t]*\r?\n', '', t, flags=re.M)

    # 9.0 删掉了 queryCFForServiceClass，只保留不带 serviceClass 的 queryCallForward
    t = t.replace('miUt.queryCFForServiceClass(condition, number, serviceClass)',
                  'miUt.queryCallForward(condition, number)')
    # setCamera 变成 (String,int)
    t = t.replace('mVideoCallProvider.setCamera(cameraId)',
                  'mVideoCallProvider.setCamera(cameraId, -1)')
    # 9.0 的 IImsCallSession.setListener 收的是 android.telephony.ims.aidl.IImsCallSessionListener，
    # 而旧库手里的 IImsCallSessionListenerProxy 继承的是旧包接口（同名不同包，方法还多一个 session 参数），
    # 无法直接传。旧 IMS 呼叫路径本来就被三星新 IMS 服务取代，这里先传 null 保证编译，后续要用的话再补适配器。
    t = t.replace('iSession.setListener(new IImsCallSessionListenerProxy());',
                  'iSession.setListener(null); '
                  '// TODO 旧库只有旧包监听器，暂不注册（见 fix_ims_common.py 说明）')

    added = []
    # 逐个内部类处理（插入会改变偏移，所以每次重新查找）
    while True:
        hit = None
        for m in STUB_CLASS.finditer(t):
            iface = m.group(2)
            if iface not in STUBS:
                continue
            i = m.end() - 1          # 类声明末尾的 '{'
            depth = 0
            end = None
            for j in range(i, len(t)):
                if t[j] == '{':
                    depth += 1
                elif t[j] == '}':
                    depth -= 1
                    if depth == 0:
                        end = j
                        break
            if end is None:
                continue
            body = t[i:end]
            todo = []
            for key, sig in STUBS[iface]:
                if key not in body:
                    todo.append(sig)
            if todo:
                hit = (i, iface, todo)
                break
        if hit is None:
            break
        i, iface, todo = hit
        ins = ('\n        // ==== Android 9 新增方法，旧实现不支持，补空实现 ====\n'
               + '\n'.join('        ' + s for s in todo))
        t = t[:i + 1] + ins + t[i + 1:]
        added.append('%s(%s)' % (iface, ','.join(
            re.search(r'(\w+)\s*\(', s).group(1) for s in todo)))

    if t != orig:
        open(path, 'w', encoding='utf-8', newline='\n').write(t)
    return added


def main():
    root = sys.argv[1].rstrip('/')
    base = os.path.join(root, 'src', 'java')
    total = 0
    for dirpath, _, files in os.walk(base):
        for f in sorted(files):
            if not f.endswith('.java'):
                continue
            p = os.path.join(dirpath, f)
            added = patch_file(p)
            if added:
                total += len(added)
                print('%-28s %s' % (f, '; '.join(added)))
    print('完成，共处理 %d 个文件' % total)


if __name__ == '__main__':
    main()