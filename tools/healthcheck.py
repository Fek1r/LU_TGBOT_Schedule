"""Container liveness probe.

The bot listens on no port, so "is it alive" cannot be answered with an HTTP
request. Instead the cancellation job touches a heartbeat file on every round;
if that file goes stale the process is wedged even though it never exited.

Deliberately does not talk to Telegram: a second getUpdates call would be a
competing poller, and Telegram resolves those by killing one of them.
"""
import os
import sys
import time

path     = os.getenv("HEARTBEAT_FILE", "/data/heartbeat")
interval = int(os.getenv("CHECK_INTERVAL_MINUTES", "20"))
limit    = interval * 60 * 3          # three missed rounds

try:
    age = time.time() - os.path.getmtime(path)
except OSError:
    print(f"no heartbeat at {path}", file=sys.stderr)
    sys.exit(1)

if age > limit:
    print(f"heartbeat is {age / 60:.0f} min old, limit {limit / 60:.0f}", file=sys.stderr)
    sys.exit(1)

sys.exit(0)
