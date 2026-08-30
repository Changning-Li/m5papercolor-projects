#!/usr/bin/env python3
"""Read serial output from PaperColor device (no reset).

Usage: python3 read_serial.py [seconds] [port]
"""
import os, sys, time, select, subprocess, glob

secs = float(sys.argv[1]) if len(sys.argv) > 1 else 20.0
if len(sys.argv) > 2:
    port = sys.argv[2]
else:
    ports = sorted(glob.glob('/dev/cu.usbmodem*'))
    if not ports:
        raise SystemExit("No /dev/cu.usbmodem* serial device found")
    port = ports[0]

subprocess.run(['stty', '-f', port, '115200', 'cs8', '-cstopb', '-parenb', '-ixon', '-ixoff', 'raw'], timeout=3)

fd = os.open(port, os.O_RDONLY | os.O_NONBLOCK)

print(f"Reading from {port} ({secs:.0f}s)...", flush=True)
end = time.time() + secs
buf = b''
while time.time() < end:
    r, _, _ = select.select([fd], [], [], 0.3)
    if r:
        try:
            data = os.read(fd, 4096)
            if data:
                buf += data
                print(data.decode('utf-8', errors='replace').rstrip(), flush=True)
        except OSError:
            pass

os.close(fd)
print("\n=== Total bytes:", len(buf), "===")
