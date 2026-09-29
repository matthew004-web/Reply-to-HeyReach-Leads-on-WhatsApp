#!/usr/bin/env bash
# Two ways to run the loop:
#
# A) Scheduled digest (a few times a day is plenty):
#      crontab -e
#      0 9,13,17 * * 1-5  /path/to/heyreach-inbox-digest/examples/cron.sh digest
#
# B) Near-instant alerts ("ping me in under a minute"):
#    run watch.py persistently (tmux/screen/systemd) — it polls every ~2 min
#    and fires your notifier the moment a reply lands:
#      python3 watch.py --interval 120 --notify-cmd "python3 examples/notify_telegram.py"
#
set -euo pipefail
cd "$(dirname "$0")/.."

# Keep the key out of the repo: export it here or in your environment.
# export HEYREACH_API_KEY="..."

mode="${1:-digest}"
if [ "$mode" = "watch" ]; then
  exec python3 watch.py --interval 120
else
  python3 digest.py --out-dir out
  # Optional: push to Telegram (see examples/notify_telegram.py)
  # python3 examples/notify_telegram.py
fi
