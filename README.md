# Local AI — Pocket Node

Run a private AI agent on the phone you already own. Not a chatbot: an agent that reads, writes
and surgically edits files in your own notes vault, entirely on-device, and keeps working in
airplane mode.

This repository will become two things at once — the workbook for a 105-minute hands-on session,
and a standalone guide anyone can follow on their own to set up the same system with no prior
background.

> ## Status: M0 — validation spike
>
> **Not ready to follow yet.** Nothing here is a setup guide. This milestone exists to test the
> handful of assumptions the design rests on, on a real phone, before any of it gets built.
>
> The design is complete (`spec/`), the open questions are tracked (`VALIDATION.md`), and the
> probes that answer them are in `probes/`. The toolkit, the vault template and the session
> materials come next — and deliberately not before the probes come back.

## Why validate first

The design depends on things no amount of desk research settles. The sharpest one:

**Will the harness talk to a server running on the phone itself?** Google AI Edge Gallery's
documentation says it *"requires the local server to have a publicly routable URL"*. If that is
true as written, the phone cannot host its own tool server, and an entire branch of the design
has to change. Documentation lags apps often enough that it is worth ten minutes and a real
device to find out — and cheap to discover now, expensive to discover after the toolkit is built
on top of it.

That question is [V2 in the register](VALIDATION.md). There are 23 others.

## What is here

| Path | What it is |
|---|---|
| `spec/` | The full Phase 1 design specification, unmodified |
| `VALIDATION.md` | Every open assumption, its status, and the evidence that settled it |
| `probes/README.md` | The test protocol — phone setup, then the probes, then how to record results |
| `probes/mcp-prototype/` | A throwaway MCP server used to test whether the harness will connect to it |
| `probes/ios/` | An a-Shell environment probe, waiting on an iPhone |
| `skills/` | Two probe skills, published to GitHub Pages so the harness can load them |

## The design in one paragraph

A single agent harness (Google AI Edge Gallery) runs an open-weight model on the phone —
Gemma 4 E2B for capability, Qwen3.5-0.8B as a deliberate contrast. A terminal (Termux on Android,
a-Shell on iOS) runs `pocketkit`, one dependency-free Python file that owns the rules. All input
and output flows through a dedicated Obsidian vault with fixed folders: the AI may only create
in `10-Drafts`, may never touch `20-Sources` or `50-Skills`, and only a human promotes a draft
into the curated folders. Those rules live in code, not in a prompt, because a prompt is a
request and code is a guarantee. Every state-changing action is approved by the person, and
everything works offline once installed.

Full detail: [`spec/Local_AI_Workshop_Phase1_Pocket_Node_Design_Spec.md`](spec/Local_AI_Workshop_Phase1_Pocket_Node_Design_Spec.md).

## Running the probes

You need an Android phone (12+, 6 GB RAM, 10 GB free) and about 90 minutes, most of it waiting
for models to download. Start at [`probes/README.md`](probes/README.md).

Results are the deliverable — **failures especially**. A probe that fails and says why is worth
more than one that passes vaguely.

## Verifying the probe server on a computer

The MCP prototype is standard-library Python and runs anywhere, so its protocol can be proven
correct before it ever meets a phone. If it then fails on the device, the fault is not ours:

```bash
cd probes/mcp-prototype
python3 test_probe_serve.py     # 23 tests, no dependencies
python3 probe_serve.py          # then, in another terminal:
sh curl-checks.sh               # 10 checks over a real socket
```

## Licence

Apache 2.0, matching the models this project is built around.
