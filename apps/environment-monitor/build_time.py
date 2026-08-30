# PlatformIO 预构建脚本
# 把「编译时刻的 Unix 时间戳」注入固件, 用于在没有 WiFi 的情况下给 RTC 对时。
# 用绝对时间戳(UTC epoch)而不是 __TIME__ 字符串, 可避免受编译主机时区影响。
# 另外: 每次 pio run 这个值都会变, 强制 PlatformIO 重新编译,
# 保证烧录时写入的时间就是"当下"。

import time

Import("env")  # noqa: F821  (PlatformIO 注入)

env.Append(CPPDEFINES=[("BUILD_UNIX_TIME", int(time.time()))])
