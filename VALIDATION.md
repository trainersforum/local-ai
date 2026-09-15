# Validation Register

The design spec marks 22 items `[VERIFY]` because they depend on app behaviour that cannot be
known from a desk. This file is where each one gets an answer and evidence. It is the spine of
the project: **no milestone may rely on an item that is still `PENDING`**, and a claim without
evidence in the Evidence column does not count as resolved.

Source: `spec/Local_AI_Workshop_Phase1_Pocket_Node_Design_Spec.md` §16. Items V23+ were found
during M0 and are not in the original spec.

## Status vocabulary

| Status | Meaning |
|---|---|
| `RESOLVED-TRUE` | Verified true. Evidence recorded. Build on it. |
| `RESOLVED-FALSE` | Verified false. The fallback in the last column is now the plan. |
| `PENDING-TEST` | Testable on the Android device now, via `probes/README.md`. |
| `PENDING-DEVICE` | Blocked on the iPhone, which has not been acquired. |
| `AT-RISK` | Desk research suggests this will fail. Treat the fallback as the likely path. |

## Current state — 2026-09-16

**Resolved: 5 · At risk: 1 · Pending test (Android): 11 · Pending device (iPhone): 9**

M0 acceptance (spec §9.1) needs **V1, V2, V4, V10, V13** resolved on Android. Two are done
(V10, V13); three need the phone (V1, V2, V4). **V2 is the one that can change the architecture.**

---

## Register

| # | Item | Status | Evidence | Decision impact / fallback |
|---|---|---|---|---|
| **V1** | `run_js` skills execute in Gallery (`quant-calculator` probe) | `PENDING-TEST` (Android) · `PENDING-DEVICE` (iOS) | — | If false: text-only skills only; `vault-bridge` becomes a text-only skill that emits op JSON. Probe A in `probes/README.md`. The `vault-guide-probe` control skill separates "JS broken" from "skills broken". |
| **V2** | Gallery MCP accepts `http://127.0.0.1:8765/mcp` with a custom header | **`AT-RISK`** · `PENDING-TEST` | Gallery's own MCP docs state the app *"requires the local server to have a publicly routable URL"* and recommend Cloudflare Quick Tunnels. Docs may lag the app — must be tested, not assumed. | **If false, the Android L1 autonomous loop is unreachable offline.** The assisted route (§7.5) becomes primary on *both* platforms and MCP drops to optional/Phase 2 — a revision to §6.1, §7.4, §8, §11.2, §12. Probe B. |
| **V3** | Gallery MCP availability on iOS | `RESOLVED-FALSE` (as of 2026-09-16) | Google Developers Blog: MCP "is an experimental feature in the Android app. The update to the iOS app is coming soon." Gallery `mcp/` docs mention Android only. | iOS stays on the assisted route regardless. Re-check before release. |
| **V4** | `pk serve` survives in Termux while Gallery is foreground 30+ min | `PENDING-TEST` | — | Wake lock + battery unrestricted + restart instructions. Worth running even if V2 fails — the §7.9 Telegram follow-up needs the same longevity. Probe C. |
| **V5** | a-Shell `pickFolder` grants persistent read/write to `On My iPhone/Obsidian/PocketBrain` | `PENDING-DEVICE` | a-Shell docs confirm `pickFolder` bookmarks directories in other apps' sandboxes, with `showmarks`/`jump`. Persistence and write access untested. | Vault inside a-Shell's own Documents, opened in Obsidian via "Open folder as vault"; else manual copy. `probes/ios/ashell-probe.sh` tests this. |
| **V6** | `pbcopy`/`pbpaste` in a-Shell; `termux-clipboard-*` in Termux | `PENDING-TEST` (Android) · `AT-RISK`/`PENDING-DEVICE` (iOS) | a-Shell's documented command list does **not** mention `pbcopy`/`pbpaste`. | `pk apply -` then paste, ending with Ctrl-D. Already in spec §7.3, so a false result costs documentation wording, not design. |
| **V7** | a-Shell `curl` + `tar -xzf`; Shortcuts Put File / Execute Command reach the bookmarked folder in App mode | `PENDING-DEVICE` | a-Shell exposes Execute Command, Put File and Get File, with "In App" and "In Extension" modes. | Download the zip via Safari into the a-Shell folder. |
| **V8** | Tapping `obsidian://adv-uri` links from Gallery skill output opens Obsidian | `PENDING-DEVICE` (also testable on Android) | — | Route A (`pk apply`) only. |
| **V9** | Advanced URI parameters for create/overwrite/append at a heading; practical URL length | `PENDING-DEVICE` | — | Route A only. The `vault-bridge` skill already falls back when the encoded link exceeds ~1,800 characters. |
| **V10** | Qwen3.5-0.8B `.litertlm` import by HF URL works; size | `RESOLVED-TRUE` (repo) · `PENDING-TEST` (import) | `huggingface.co/litert-community/Qwen3.5-0.8B` exists, Apache-2.0, not gated. Contains **`Qwen3.5-0.8B_int8.litertlm` (963 MB)** and **`Qwen3.5-0.8B-VL_int8.litertlm` (1.3 GB, vision)**. | The spec's URL was correct and the size blank is now filled. The VL variant is a bonus the spec does not anticipate — probe it, since it would give the *contrast* model image input. Import-by-URL still needs the device. Probe D. |
| **V11** | Gemma 4 E2B offered and runs on a 6 GB iPhone in Gallery | `PENDING-DEVICE` | — | Qwen3.5-0.8B for the loop; Gemma demoed on the facilitator phone. |
| **V12** | Agent Chat usable context for tool loops | `PENDING-TEST` | — | Lower `read_chars` from 4,000; fewer steps per request. |
| **V13** | Gallery accepts `metadata:` schema keys in `SKILL.md` | `RESOLVED-TRUE` | Gallery `skills/README.md` documents a `metadata:` block (`homepage`, `require-secret`, `require-secret-description`) and permits unknown keys inside it. | Vault schema keys (`type`/`source`/`status`) live under `metadata:`. Companion notes in `50-Skills/` are not needed. Both M0 probe skills are built this way, so the device test confirms it in passing. |
| **V14** | Local skill folder import on iOS | `PENDING-DEVICE` | Android imports a folder via the file picker (`adb push` then pick). No iOS equivalent documented. | URL import only on iOS. |
| **V15** | Exact URL form for "Add from URL" (directory vs file) | `RESOLVED-TRUE` | Gallery `skills/README.md`: *"The url should be pointing to the **skill folder** itself."* Verify by checking the raw `SKILL.md` renders in a browser. | Docs and QR codes point at `…/skills/<name>/` **with** the trailing slash. |
| **V16** | Native email/text intents available on iOS Gallery | `PENDING-DEVICE` | — | Copy text into Mail manually. |
| **V17** | Agent Chat accepts image/audio attachments directly | `PENDING-TEST` | — | Keep Ask Image and Audio Scribe as separate input steps, which is what §12 D1/D2 already assume. |
| **V18** | `pip install pypdf` works in a-Shell and Termux | `PENDING-TEST` (Android) · `PENDING-DEVICE` (iOS) | a-Shell's `pip` is confirmed pure-Python only; `pypdf` is pure Python, so this should hold. | Termux: `pkg install poppler` (`pdftotext`). iOS: copy text out of a PDF viewer. |
| **V19** | App Store links for Obsidian and a-Shell | `PENDING-DEVICE` | Gallery iOS confirmed at App Store id `6749645337`. Obsidian and a-Shell links not yet checked. | Search by name in the App Store. |
| **V20** | Gemma 4 E2B catalog name and current checkpoint in Gallery; **actual download size** | `PENDING-TEST` | `litert-community/gemma-4-E2B-it-litert-lm` exists. LiteRT-LM reportedly uses a mixed 2/4/8-bit scheme: ~0.8 GB text-only weights plus ~1.12 GB memory-mapped embeddings. | This does **not** obviously match the "≈ 2.6 GB" quoted to participants in §10.1 step 8. People plan storage and download time around that number, so it must be measured on the device. Probe D. |
| **V21** | Locally AI Shortcuts action parameters; Gemma 4 on a 6 GB iPhone (follow-up L4) | `PENDING-DEVICE` | — | Drop the L4 follow-up. |
| **V22** | llama.cpp availability/performance in Termux with a small GGUF (follow-up messaging) | `PENDING-TEST` | Gallery imports `.litertlm` **only**, not GGUF — so GGUF models belong here, not in the session. `unsloth/Qwen3-VL-2B-Instruct-GGUF` is a candidate for this bridge. | Limit the bridge to Qwen-class GGUF, or defer to Phase 2. |
| **V23** *(new)* | Which MCP protocol revision does Gallery actually request? | `PENDING-TEST` | MCP added a `2026-07-28` revision that removed the GET stream endpoint and protocol-level sessions. Spec §7.4 lists only `2025-03-26`, `2025-06-18`, `2025-11-25`. | `probe_serve.py` speaks all four and **logs what Gallery asks for**, which decides what M3 is built against. Stateless + no GET already matches the 2026 shape. |
| **V24** *(new)* | GitHub Pages serves `SKILL.md` and `scripts/index.html` with usable Content-Types | `PENDING-TEST` | Gallery docs: GitHub raw URLs serve `text/plain`, which "lacks the proper MIME types required for execution" — real hosting is required. | If Pages is also unusable, skills need different hosting. Blocks V1, so it is checked first. |

---

## Updating this file

1. Run the probes in `probes/README.md`.
2. Commit raw output to `probes/results/` — **verbatim logs, not summaries**. An exact error
   string is the difference between a fix and a guess.
3. Move the row's Status and paste the decisive line into Evidence, with the date.
4. When a row resolves `FALSE`, apply the fallback in the last column and note which spec
   sections need changing. `probes/FINDINGS.md` collects those into one decision.
