#!/usr/bin/env bash
# Best-effort fetch of a LIVE Excalidraw collab room's current scene, decrypted
# locally, and written out in standard .excalidraw file format so it can be
# piped straight into extract_region.py.
#
# Usage:
#   fetch_room.sh "https://excalidraw.com/#room=<roomId>,<key>" > out.excalidraw
#
# This talks to Excalidraw's own (undocumented, unofficial) public storage
# backend -- a Firestore document per room, containing an AES-128-GCM
# ciphertext encrypted with the key that lives in the URL fragment and never
# leaves this machine. It relies on that endpoint's current shape, so it can
# break at any time; treat any failure as expected, not a bug to chase.
#
# Requires: curl, node (built-in `crypto` module only -- no npm install, no
# packages). If node is not installed, or anything else about this fails,
# this script exits non-zero and prints nothing to stdout. Per SKILL.md, a
# non-zero exit here means: stop, and ask the user for an exported
# .excalidraw file instead -- do not retry, do not attempt an alternate
# decrypt method (no pip installs, no venvs), do not try again with the same
# link.
set -euo pipefail

if [ -z "${1:-}" ]; then
  echo "Usage: fetch_room.sh <excalidraw.com/#room=...,... URL>" >&2
  exit 2
fi

if ! command -v node >/dev/null 2>&1; then
  echo "fetch_room.sh: node is not installed -- cannot decrypt. Ask the user for an exported .excalidraw file." >&2
  exit 3
fi

url="$1"
case "$url" in
  *"#room="*) ;;
  *)
    echo "fetch_room.sh: not a room link (no #room= fragment). Ask the user for an exported .excalidraw file." >&2
    exit 2
    ;;
esac

frag="${url#*#room=}"
room_id="${frag%%,*}"
key_b64url="${frag#*,}"

if [ -z "$room_id" ] || [ -z "$key_b64url" ] || [ "$key_b64url" = "$frag" ]; then
  echo "fetch_room.sh: could not parse roomId/key from URL. Ask the user for an exported .excalidraw file." >&2
  exit 2
fi

doc_json=$(curl -sS --fail "https://firestore.googleapis.com/v1/projects/excalidraw-room-persistence/databases/(default)/documents/scenes/${room_id}") \
  || { echo "fetch_room.sh: fetch failed (room not cloud-persisted, network error, or endpoint changed). Ask the user for an exported .excalidraw file." >&2; exit 4; }

echo "$doc_json" | node -e '
const crypto = require("crypto");
let raw = "";
process.stdin.on("data", d => raw += d);
process.stdin.on("end", () => {
  try {
    const doc = JSON.parse(raw);
    if (!doc.fields || !doc.fields.iv || !doc.fields.ciphertext) {
      process.stderr.write("fetch_room.sh: unexpected response shape (endpoint may have changed). Ask the user for an exported .excalidraw file.\n");
      process.exit(5);
    }
    const iv = Buffer.from(doc.fields.iv.bytesValue, "base64");
    const ct = Buffer.from(doc.fields.ciphertext.bytesValue, "base64");
    const body = ct.subarray(0, ct.length - 16);
    const tag = ct.subarray(ct.length - 16);

    const keyUrl = process.argv[1].replace(/-/g, "+").replace(/_/g, "/");
    const pad = "=".repeat((4 - keyUrl.length % 4) % 4);
    const key = Buffer.from(keyUrl + pad, "base64");

    const decipher = crypto.createDecipheriv("aes-128-gcm", key, iv);
    decipher.setAuthTag(tag);
    const elements = JSON.parse(Buffer.concat([decipher.update(body), decipher.final()]));

    const wrapped = { type: "excalidraw", version: 2, source: "fetch_room.sh", elements, files: {} };
    process.stdout.write(JSON.stringify(wrapped));
  } catch (e) {
    process.stderr.write("fetch_room.sh: decrypt failed (" + e.message + "). Ask the user for an exported .excalidraw file.\n");
    process.exit(6);
  }
});
' "$key_b64url"
