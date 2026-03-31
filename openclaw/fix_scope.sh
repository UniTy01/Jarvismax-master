#!/bin/bash
# Fix OpenClaw operator scopes on Hostinger VPS
# Usage: bash openclaw/fix_scope.sh

set -e
CONFIG=/data/.openclaw/openclaw.json
echo '[+] Fixing operator scopes...'

if command -v openclaw &>/dev/null; then
  openclaw config set gateway.remote.scopes 'operator.read,operator.write,operator.admin,operator.pairing'
  echo '[+] Done via openclaw CLI'
  exit 0
fi

if command -v jq &>/dev/null; then
  jq '.gateway.remote.scopes = ["operator.read","operator.write","operator.admin","operator.pairing"]' \
    $CONFIG > /tmp/oc_new.json && mv /tmp/oc_new.json $CONFIG
  echo '[+] Done via jq'
  exit 0
fi

python3 -c "
import json
cfg = json.load(open('/data/.openclaw/openclaw.json'))
cfg.setdefault('gateway', {}).setdefault('remote', {})['scopes'] = ['operator.read','operator.write','operator.admin','operator.pairing']
json.dump(cfg, open('/data/.openclaw/openclaw.json', 'w'), indent=2)
print('[+] Done via Python')"
