# M0 Probe Protocol

Everything in the design spec that depends on how an app actually behaves is unverified until
someone runs it on a real phone. This document is that run. Work through it in order and record
what happens — including, especially, the things that fail.

**The goal is evidence, not success.** A probe that fails cleanly and tells us *why* is worth
more than one that passes vaguely. Copy exact error messages; do not paraphrase them.

Time: about 90 minutes, most of it model downloads.

| Probe | Resolves | Needs |
|---|---|---|
| [A — Skills](#probe-a--skills) | V1, V13, V15, V24 | Gallery, internet |
| [B — MCP loopback](#probe-b--mcp-loopback) | **V2**, V23 | Termux + Gallery |
| [C — Server survival](#probe-c--server-survival) | V4 | 30 min of waiting |
| [D — Models](#probe-d--models) | V10, V17, V20 | Internet, ~4 GB storage |
| [E — Environment](#probe-e--environment) | V6, V12, V18 | Termux |

**Probe B is the one that matters.** If Gallery will not talk to a server on `127.0.0.1`, the
whole "Full agent" Android path in the spec has to be redesigned. Everything else is detail by
comparison.

---

## Before you start

On the phone: **Settings › About phone** — confirm Android 12 or newer, 6 GB RAM or more.
**Settings › Storage** — confirm at least 10 GB free (the models alone are ~3.5 GB).

Write those three numbers down; they go in the results file.

---

## Part 1 — Set up the phone

### 1.1 Install Termux (not from Google Play)

The Play Store build is abandoned and broken. Use one of:

- F-Droid: <https://f-droid.org/packages/com.termux/> → **Download APK**
- GitHub: <https://github.com/termux/termux-app/releases/latest> → the **`arm64-v8a`** APK

Allow your browser to install unknown apps when prompted, then install.

Optionally also install **Termux:API** *from the same source* (mixing sources breaks signature
checks). It provides `termux-clipboard-get/set`, which probe E tests.

### 1.2 Prepare Termux

Open Termux and run these one line at a time:

```bash
pkg update && pkg upgrade -y
pkg install -y python git curl
termux-setup-storage          # tap "Allow" when Android asks
python3 --version             # expect 3.11 or newer
```

Then: **Settings › Apps › Termux › Battery › Unrestricted.** Probe C depends on this.

### 1.3 Get this repository

```bash
git clone https://github.com/trainersforum/local-ai ~/local-ai
cd ~/local-ai
```

### 1.4 Install Claude Code in Termux (recommended)

This is optional. It exists so you don't have to copy-paste probe output by hand — Claude Code
can run the probes and commit the raw logs straight back to the repo.

**Read this before running it.** There is no official Anthropic build for Android. The installer
below is a third-party shim that patches Anthropic's official arm64 Linux binary to run under
Android's Bionic C library. Two things follow from that:

- You are running a community script on the device that will hold your workshop bearer tokens.
  Download it, read it, *then* run it. That is the same discipline §7.10 of the spec asks
  participants to apply to any script.
- The installer **repoints Claude Code's DNS to 8.8.8.8 / 8.8.4.4** to avoid connectivity hangs.
  On a device that also uses a VPN, that is worth knowing about in advance.

```bash
curl -fsSL https://raw.githubusercontent.com/ferrumclaudepilgrim/claude-code-android/main/install.sh -o install.sh
less install.sh        # read it. q to quit.
bash install.sh
claude                 # follow the login prompts
```

Then set a git identity so commits from the phone are attributable:

```bash
git config --global user.name  "Your Name"
git config --global user.email "you@example.org"
```

> **Do not use the proot-distro / Ubuntu route.** It gives you a second Linux environment, and
> `pocketkit` must be validated in the **bare Termux a participant actually has**. One
> environment, one truth.

### 1.5 Clean-shell check

Claude Code pulls in `nodejs` and `glibc-runner`. Those must never become hidden requirements of
the workshop toolkit. Confirm the participant-facing baseline still stands on its own:

```bash
env -i HOME="$HOME" PATH=/data/data/com.termux/files/usr/bin sh -c \
  'python3 -c "import json, pathlib, http.server, urllib.request, secrets; print(\"stdlib OK\")"'
```

If that fails, something has leaked into the toolkit's assumptions. Record it.

---

## Part 2 — The probes

### Probe A — Skills

*Resolves V1 (`run_js` works), V13 (`metadata:` keys accepted), V15 (URL form), V24 (Pages MIME).*

Gallery cannot load JS skills from `raw.githubusercontent.com` — GitHub serves those as
`text/plain`, which will not execute. They must come from real hosting, which is why this repo
publishes to GitHub Pages.

**A1. Confirm the skills are being served.** Already verified from a desktop on 2026-09-16 —
Pages returns `text/markdown` for `SKILL.md` and `text/html` for `index.html`, so **V24 is
resolved** and the hosting is valid. Confirm it also loads on the phone. In the phone's browser,
open:

- <https://trainersforum.github.io/local-ai/skills/quant-calculator/SKILL.md>
- <https://trainersforum.github.io/local-ai/skills/quant-calculator/scripts/index.html>

Both must load. Record whether the browser **displays** them or tries to **download** them.

**A2. Add the JS skill.** Gallery › Agent Skills › Skills › **+** › *Add from URL*:

```
https://trainersforum.github.io/local-ai/skills/quant-calculator/
```

Note the **trailing slash** and that it points at the *folder*, not at `SKILL.md`.

Record: did it accept the URL? Did the skill appear with its name and description? Any error?

**A3. Add the text-only control skill.**

```
https://trainersforum.github.io/local-ai/skills/vault-guide-probe/
```

This one runs no JavaScript at all. It is here so that a failure can be localised: if
`vault-guide-probe` loads and `quant-calculator` does not, JavaScript is the problem, not skill
loading. Without this comparison a V1 failure tells us nothing.

**A4. Run the JS skill.** In Agent Chat with Gemma 4 E2B:

> Use the quant calculator for 2 billion parameters at 4.8 bits per weight.

**Pass:** a reply containing roughly `≈ 1.12 GB of weights on disk`.

**Also record the `_probe` field** if the raw tool output is visible anywhere. It reports
`typeof_data` — whether Gallery passes arguments as a JSON *string* or as an *object*. That is
undocumented, and the `vault-bridge` skill will depend on it later.

**A5. Run the text-only skill.**

> How is the vault organised and where do AI-generated notes go?

**Pass:** the folder table, with `10-Drafts` named as where AI output lands.

| What happened | Means |
|---|---|
| Both skills work | V1 TRUE, V13 TRUE, V15 TRUE. |
| Text works, JS does not | V1 FALSE. `vault-bridge` becomes text-only, emitting op JSON. Record the exact error. |
| Neither loads, URL rejected | V15 wrong — try the full `.../SKILL.md` URL and record which form works. |
| Neither loads, URL accepted | Likely V13 (frontmatter rejected) or V24 (MIME). Check A1 again. |

---

### Probe B — MCP loopback

*Resolves **V2** and V23. This is the decisive experiment.*

Gallery's own documentation says the app *"requires the local server to have a publicly routable
URL"*. If that is literally true, the spec's Android architecture does not work. Documentation
does lag behind apps, so we test it rather than believe it.

**B1. Start the probe server.** In Termux:

```bash
cd ~/local-ai/probes/mcp-prototype
python3 probe_serve.py
```

It prints the URL, the bearer token, and the exact values to type into Gallery. Leave it running.

**B2. Prove the server works on-device.** Open a *second* Termux session (swipe from the left
edge → **NEW SESSION**):

```bash
cd ~/local-ai/probes/mcp-prototype
sh curl-checks.sh
```

**Pass:** `passed: 10   failed: 0`.

If this fails, stop — the server is unhealthy and a Gallery failure would tell you nothing.
Save the output and send it.

**B3. Connect Gallery.** Gallery › Agent Chat › **MCP** › *Add MCP server*:

| Field | Value |
|---|---|
| URL | `http://127.0.0.1:8765/mcp` |
| Header name | `Authorization` |
| Header value | `Bearer <token from the server banner>` |

Record, precisely:

1. Does the UI **accept** the URL, or reject it for not being HTTPS / not being public?
2. If accepted, does it connect and list two tools (`vault_guide`, `vault_read`)?
3. Whatever the outcome — **check the Termux window**. Did anything appear?

**B4. If the URL was rejected, try `http://localhost:8765/mcp`** and record the result.

**B5. Read the log.** This is the diagnostic that matters:

```bash
cat ~/local-ai/probes/mcp-prototype/probe-requests.log
```

| Log contents | Diagnosis |
|---|---|
| **Empty** (only `server_start`) | The request never left Gallery. Client-side URL validation or Android's cleartext-HTTP policy. **V2 FALSE.** |
| Has `http_request` entries | Gallery reached the server and disagreed about something. **Recoverable** — the logged headers and body say what. Send the whole log. |

**B6. If tools listed, call one.** In Agent Chat:

> Read the vault guide and list the folders.

Record whether an **approval prompt** appears before the call (the spec's §7.10 security model
depends on it), and whether the result comes back.

**B7. Diagnostic only — never a workshop path.** If loopback failed, we still want to know
whether Gallery's MCP client works at all. Requires internet and briefly exposes the endpoint
publicly, so do this once and stop the server afterwards:

```bash
pkg install -y cloudflared
cloudflared tunnel --url http://127.0.0.1:8765
```

Give Gallery the printed `https://….trycloudflare.com/mcp` URL plus the same Authorization
header. If **this** works and loopback does not, the constraint is transport, not protocol —
a decisive finding that shapes what we build next.

**B8. Record the protocol version (V23).** In the log, find the `initialize` line and note
`client_requested_version`. That decides which MCP revision M3 is built against.

---

### Probe C — Server survival

*Resolves V4.* Only fully meaningful if B succeeded, but run it regardless — the Android
messaging bridge in §7.9 needs the same longevity.

```bash
# session 1
termux-wake-lock
cd ~/local-ai/probes/mcp-prototype && python3 probe_serve.py

# session 2
cd ~/local-ai/probes/mcp-prototype
TOKEN=$(cat .probe-token)
i=0
while [ $i -lt 30 ]; do
  printf '%s ' "$(date +%H:%M:%S)"
  curl -s -o /dev/null -w '%{http_code}\n' -X POST http://127.0.0.1:8765/mcp \
    -H 'Content-Type: application/json' -H "Authorization: Bearer $TOKEN" \
    -d '{"jsonrpc":"2.0","id":1,"method":"ping"}'
  i=$((i + 1)); sleep 60
done | tee ../results/v4-survival.log
```

Use the phone normally meanwhile — Gallery in the foreground, screen locking as usual.

**Pass:** thirty `200`s. Any gap, and note what the phone was doing.

Afterwards: `termux-wake-unlock`.

---

### Probe D — Models

*Resolves V10, V17, V20.*

**D1. Gemma 4 E2B.** Gallery › download **Gemma-4-E2B-it**. Record the **exact catalog name**
and the **actual download size**.

This matters: participants are told "≈ 2.6 GB" in the pre-session checklist and plan their
storage and mobile data around it. Published figures for the LiteRT-LM build suggest ~0.8 GB of
text-only weights plus ~1.12 GB of memory-mapped embeddings, which does not obviously add up to
2.6 GB. Measure it.

**D2. Import Qwen3.5-0.8B.** Gallery › model manager › **+** › *Import from HF*:

```
https://huggingface.co/litert-community/Qwen3.5-0.8B
```

The repository holds two files — `Qwen3.5-0.8B_int8.litertlm` (963 MB) and
`Qwen3.5-0.8B-VL_int8.litertlm` (1.3 GB, vision-capable). Record **which one Gallery takes**,
whether it offers a choice, and whether it demands a Hugging Face login.

**D3. Contrast the two models.** Same prompt to each, in fresh chats:

> Use the quant calculator for 700 million parameters at 4 bits.

Record for each: did it call the tool, was the call well-formed, how long did it take. Qwen
failing at tool calling is a legitimate and teachable result — but we need to know *how* it
fails to teach it honestly.

**D4. VL variant (stretch).** If the vision file can be imported, test an image prompt. The spec
does not anticipate this; a vision-capable 1.3 GB contrast model would be a genuine gain.

**D5. Attachments (V17).** In Agent Chat, try attaching an image and an audio clip directly.
If unsupported, Ask Image and Audio Scribe stay separate steps — which is what §12 already assumes.

---

### Probe E — Environment

*Resolves V6 (Android), V12, V18 (Android).*

```bash
# V6 - clipboard (needs the Termux:API app)
echo "pocketkit clipboard probe" | termux-clipboard-set && termux-clipboard-get

# V18 - PDF extraction
pip install pypdf && python3 -c "import pypdf; print(pypdf.__version__)"

# fallback if that fails
pkg install -y poppler && pdftotext -v
```

**V12 — usable context.** In Agent Chat with Gemma 4 E2B, ask it to read a long note and then
call a tool. Record roughly where it starts losing the thread. If it degrades well before the
4,000-character read limit in the spec, that limit has to come down.

---

## Part 3 — Recording results

Raw logs first, prose second. Copy the file below to
`probes/results/results-YYYY-MM-DD.md`, fill it in, and commit it together with any `.log` files.

```markdown
# M0 probe results — <date>

Device: <model>  ·  Android <version>  ·  <RAM> GB RAM  ·  <free> GB free
Gallery version: <from the app's settings/about>
Termux source: <F-Droid | GitHub>  ·  Python: <python3 --version>

## V1  run_js
Status: TRUE | FALSE
JS skill loaded: yes/no          Text skill loaded: yes/no
Output verbatim:
Argument form (_probe.typeof_data): string | object | not visible

## V2  MCP loopback          <-- the important one
Status: TRUE | FALSE
curl-checks.sh: passed __ / failed __
Gallery accepted the URL: yes | no  (error verbatim: ______)
Tools listed: yes | no
probe-requests.log: EMPTY | HAS ENTRIES   (attach the file)
localhost:// variant: ______
Approval prompt shown before the tool call: yes | no
Cloudflare tunnel diagnostic (B7): worked | failed | not run

## V23 protocol version
client_requested_version from the log: ______

## V4  survival
200s: __ / 30.   Gaps and what the phone was doing: ______

## V10 / V20  models
Gemma 4 catalog name: ______   Actual download size: ______ GB
Qwen3.5-0.8B import: worked | failed   File taken: int8 | VL | chose
HF login demanded: yes | no
Tool-calling contrast (D3): ______
VL variant (D4): ______

## V6 / V12 / V17 / V18
clipboard: ______   pypdf: ______   attachments: ______   context limit: ______

## Anything unexpected
<the most valuable section — surprises, confusing UI, things the spec did not predict>
```

Then push:

```bash
cd ~/local-ai
git add probes/results/
git commit -m "M0: probe results from <device>"
git push
```

If Claude Code is running the probes: commit the **raw** logs. Summaries lose the exact error
strings, and those are usually the whole answer.
