#!/bin/sh
# iOS / a-Shell environment probe -- run this when the iPhone arrives.
#
# Resolves validation items V5 (pickFolder gives persistent vault access),
# V6-iOS (clipboard), V7 (curl + tar) and V18 (pypdf) from the design spec.
#
# It only inspects and reports. It writes nothing into the vault except one
# throwaway file used to prove write access, which it then deletes.
#
#   1. Open a-Shell
#   2. pickFolder          -> choose On My iPhone > Obsidian > PocketBrain
#   3. sh ashell-probe.sh  > probe-ios.txt
#   4. Send probe-ios.txt back, or commit it to probes/results/

set -u

echo "===================================================================="
echo " a-Shell environment probe"
echo " date: $(date 2>/dev/null || echo unknown)"
echo "===================================================================="

section() { echo; echo "--- $1 ---"; }

have() {
  if command -v "$1" >/dev/null 2>&1; then
    echo "  YES  $1"
    return 0
  fi
  echo "  NO   $1"
  return 1
}

section "V-none: shell and system"
echo "  uname : $(uname -a 2>/dev/null || echo unavailable)"
echo "  pwd   : $(pwd)"
echo "  HOME  : ${HOME:-unset}"

section "V18a: Python"
if have python3; then
  echo "  version: $(python3 --version 2>&1)"
  # The toolkit targets >= 3.11; anything older changes what pocketkit may use.
  python3 -c 'import sys; print("  version_info:", tuple(sys.version_info[:3])); print("  ok_for_pocketkit:", sys.version_info >= (3, 11))' 2>&1
  echo "  stdlib spot-check:"
  python3 -c 'import json, pathlib, http.server, urllib.request, secrets; print("    json/pathlib/http.server/urllib/secrets all import")' 2>&1
else
  echo "  python3 missing -- pocketkit cannot run here at all."
fi

section "V18b: pypdf (optional, for pk extract)"
if have pip; then
  echo "  attempting: pip install pypdf"
  pip install pypdf 2>&1 | tail -5
  python3 -c 'import pypdf; print("  pypdf version:", pypdf.__version__)' 2>&1
else
  echo "  pip missing; PDF extraction will need the manual fallback."
fi

section "V6-iOS: clipboard"
# a-Shell's docs do not mention pbcopy/pbpaste. If they are absent, the fallback
# is `pk apply -` with a manual paste, which is already in the spec (7.3).
have pbcopy || true
have pbpaste || true
if command -v pbcopy >/dev/null 2>&1 && command -v pbpaste >/dev/null 2>&1; then
  echo "pocketkit-clipboard-probe" | pbcopy 2>/dev/null
  got=$(pbpaste 2>/dev/null)
  if [ "$got" = "pocketkit-clipboard-probe" ]; then
    echo "  ROUND TRIP OK -- clipboard is usable, route A can be one command."
  else
    echo "  ROUND TRIP FAILED (read back: '$got') -- use 'pk apply -' fallback."
  fi
else
  echo "  Not both present -> V6-iOS is FALSE. Use 'pk apply -' + manual paste."
fi

section "V7: download and unpack tools"
have curl || true
have tar || true
have git || true
have unzip || true

section "V5: vault access via pickFolder bookmarks"
have showmarks || true
have jump || true
echo "  bookmarks currently registered:"
showmarks 2>&1 | sed 's/^/    /' || echo "    (showmarks unavailable)"
echo
echo "  Looking for a PocketBrain bookmark..."
if showmarks 2>/dev/null | grep -qi pocketbrain; then
  echo "  FOUND. Testing write access..."
  if jump PocketBrain 2>/dev/null; then
    echo "  jumped to: $(pwd)"
    echo "  contents:"
    ls -la 2>&1 | head -20 | sed 's/^/    /'
    probe_file=".pocketkit-write-probe"
    if echo "write probe $(date 2>/dev/null)" > "$probe_file" 2>/dev/null; then
      echo "  WRITE OK   -> $(pwd)/$probe_file"
      cat "$probe_file" 2>/dev/null | sed 's/^/    /'
      rm -f "$probe_file" && echo "  DELETE OK  (probe file removed)"
      echo "  => V5 looks TRUE: persistent read/write access to the vault."
    else
      echo "  WRITE FAILED -- bookmark is read-only or stale."
      echo "  => V5 FALSE. Re-run pickFolder, or fall back to a vault inside"
      echo "     a-Shell's own Documents opened via 'Open folder as vault'."
    fi
  else
    echo "  jump failed -- bookmark is stale. Re-run pickFolder."
  fi
else
  echo "  NOT FOUND."
  echo "  Run 'pickFolder' and choose On My iPhone > Obsidian > PocketBrain,"
  echo "  then run this probe again."
fi

echo
echo "===================================================================="
echo " done -- send this whole output back"
echo "===================================================================="
