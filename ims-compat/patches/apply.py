#!/usr/bin/env python3
"""给 frameworks/base 打两个 Android 9 API 补丁（7.1 缺失）。

用法: apply.py <frameworks/base 路径>
  - IntDef.prefix()                （Android 9 的注解成员）
  - RemoteCallbackList.broadcast() （Android 9 新增方法）
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def patch_intdef(path):
    t = open(path, encoding='utf-8').read()
    if 'prefix()' in t:
        print('IntDef.prefix() 已存在')
        return
    anchor = '\n    long[] value() default {};\n'
    ins = ('\n    /**\n'
           '     * @hide\n'
           '     */\n'
           "    String[] prefix() default {};\n")
    if anchor not in t:
        print('WARN: IntDef 锚点未找到')
        return
    open(path, 'w', encoding='utf-8', newline='\n').write(t.replace(anchor, anchor + ins, 1))
    print('patched IntDef.prefix()')


def patch_rcl(path):
    t = open(path, encoding='utf-8').read()
    if 'void broadcast(' in t:
        print('RemoteCallbackList.broadcast() 已存在')
        return
    snippet = open(os.path.join(HERE, 'rcl_broadcast.txt'), encoding='utf-8').read().rstrip('\n')
    i = t.rstrip().rfind('}')
    if i < 0:
        print('WARN: RemoteCallbackList 未找到结尾 }')
        return
    open(path, 'w', encoding='utf-8', newline='\n').write(t[:i] + snippet + '\n' + t[i:])
    print('patched RemoteCallbackList.broadcast()')


if __name__ == '__main__':
    base = sys.argv[1].rstrip('/')
    patch_intdef(os.path.join(base, 'core/java/android/annotation/IntDef.java'))
    patch_rcl(os.path.join(base, 'core/java/android/os/RemoteCallbackList.java'))