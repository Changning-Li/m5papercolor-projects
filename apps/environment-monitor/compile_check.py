#!/usr/bin/env python3
"""Run PlatformIO compile and capture output."""
import subprocess
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

# Set up environment
env = os.environ.copy()
env['PATH'] = os.path.expanduser('~/.platformio/penv/bin') + ':' + env.get('PATH', '')

result = subprocess.run(
    ['pio', 'run'],
    capture_output=True,
    text=True,
    cwd=PROJECT_ROOT,
    env=env,
    timeout=300
)
output = result.stdout + '\n' + result.stderr
# Print last 3000 chars
if len(output) > 3000:
    print('...(truncated)...')
    print(output[-3000:])
else:
    print(output)
print(f'\nEXIT CODE: {result.returncode}')
raise SystemExit(result.returncode)
