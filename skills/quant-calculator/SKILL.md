---
name: quant-calculator
description: Estimate the on-disk and in-memory size of a quantised open-weight language model from its parameter count and bits-per-weight. Use when the user asks how big a model is, whether a model fits on their phone, or what a quantisation level costs in size or quality.
metadata:
  homepage: https://trainersforum.github.io/local-ai/skills/quant-calculator/
  type: skill
  source: human
  status: reviewed
---

# Quant calculator

## Instructions

Use this skill whenever the user asks about model size, memory footprint, or whether a
given model will fit on a device.

1. Work out two numbers from the user's question:
   - `params_b` — parameter count in **billions** (a "2B" model is `2`, a "0.8B" model is `0.8`).
   - `bpw` — **bits per weight** of the quantisation. If the user names a format instead of a
     number, convert it: `f16`/`fp16` → 16, `q8`/`int8` → 8, `q5` → 5, `q4`/`int4`/`Q4_0` → 4.5,
     `q3` → 3.5, `q2` → 2.5. Mixed schemes such as LiteRT-LM's 2/4/8-bit mobile quantisation are
     roughly 4 — say that you approximated.
2. Call the tool with those two values.
3. Report the weights-only figure and the estimated runtime figure, and say plainly whether it
   fits the device in question. A phone with 6 GB of RAM has roughly 3–3.5 GB usable for a model
   once the OS and other apps are accounted for.
4. If the user has not said which device they mean, assume a 6 GB phone and state that assumption.

Do not invent benchmark scores, quality percentages or tokens-per-second numbers — this skill
estimates size only.
