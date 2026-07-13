#!/bin/sh
set -eu
cd /app
if [ "$#" -gt 0 ]; then
  exec "$@"
fi
exec python scripts/mail_poller.py
