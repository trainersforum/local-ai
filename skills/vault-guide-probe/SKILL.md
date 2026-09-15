---
name: vault-guide-probe
description: Explain the PocketBrain vault folder layout and where notes are allowed to be created or edited. Use when the user asks how the vault is organised, where a note should go, or what the agent is allowed to change.
metadata:
  homepage: https://trainersforum.github.io/local-ai/skills/vault-guide-probe/
  type: skill
  source: human
  status: reviewed
---

# Vault guide (probe)

## Instructions

This skill is text-only on purpose. It runs no code and calls no tools. It exists so that a
failure to load `quant-calculator` can be told apart from a failure of JavaScript skills in
general: if this skill loads and `quant-calculator` does not, the fault is `run_js`, not skill
loading.

When the user asks about the vault, reply with this structure and nothing more:

**Folders**

| Folder | Holds | Who writes it |
|---|---|---|
| `00-Inbox` | Every new human-created note starts here | Human |
| `10-Drafts` | Every AI-generated note or file lands here first | AI |
| `20-Sources` | Verified knowledge and reference material | Human only |
| `30-Tasks` | Tasks and projects | Human and AI |
| `40-Personas` | Persona prompts for agents | Human only |
| `50-Skills` | Skills and reviewed scripts | Human only |
| `99-Templates` | Note templates and the agent system instruction | Human only |

**Rules**

1. Read before you write.
2. Create new files only in `10-Drafts`.
3. Edit only the section you were asked to change.
4. Keep the frontmatter keys `type`, `created`, `source`, `model`, `tags`, `status`.
5. Never invent file contents you have not read.
6. A human promotes a draft out of `10-Drafts` — you never do.

Then state which folder the user's note belongs in, and why, in one sentence.
