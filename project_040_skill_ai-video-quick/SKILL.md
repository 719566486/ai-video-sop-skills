---
name: ai-video-quick
description: Make a visually striking finished video sample of up to 30 seconds from one or two sentences and optional images, using native Codex images, Kling motion and fast local editing. Use when the user prioritizes a quick short-form result with minimal co-creation, rather than a full production bible or long film.
---

# AI Video Quick

Return a playable short video fast. The creative decisions are yours unless the user specifies them. Do not turn this into the full-film interview or produce only a planning document. Read [providers](references/providers.md) for actual tool operations and [production contract](references/production-contract.md) for the small manifest and local helpers. This skill installs and runs independently of the full skill.

## Defaults and scope

- Default **15 seconds, 9:16, 1080p, 30 fps**; explicit user choices win, with a hard sample limit of 30 seconds. If the user requests longer, explain the limit and offer the full skill, never silently truncate their story.
- One clear visual idea, at most one main character/product, one primary setting (two only when needed), one style. Aim for a visible hook in the first 1–2 seconds, two or three developments and a decisive payoff/clean ending. No default black opening or long title card.
- Usually **3–4 generated source shots**, maximum four in this fast mode. Derive 4–7 short editorial beats by choosing useful source ranges, not by generating many redundant clips. Shorter one-shot requests stay one shot; don't force a montage. Avoid repeating the same motion or treating shot count as quality.
- Default music/FX-led with concise optional text, no talking head or exact lip sync unless requested. Do not add invented product claims. If the user's idea depends on spoken words, provide them with authorized audio, not a silent substitute.
- Use one style anchor and only the identity/prop references necessary for these shots. No mandatory multi-angle atlas, alternative pitch deck, or full storyboard approval round. Preserve a supplied identity or brand even in quick mode.

## Fast execution path

1. Briefly state the chosen direction and timing; start. Ask only about a true missing prerequisite or authorization. Infer optional style choices. Preflight native imagegen, Kling live capabilities/account and FFmpeg; reuse existing setup and authorization. Do not invent a completion-time guarantee for a queued service.
2. `init --mode quick` creates `production.json`. Write a compact `BRIEF.md` and fill a 3–4 row shot plan (or fewer): hook, reveal/development, payoff. Each row still has start/action/end, framing, camera, text/audio and continuity constraints. Set exact integer frame counts totaling the requested length, no more than 30 seconds. Fill every frame prompt before generation; keep `assets` small.
3. Generate the anchor and clean shot frames with the **built-in image tool**, then inspect them. Use reference-image edits to preserve identity. Don't feed a contact sheet as a literal scene. Copy selected outputs into the project. Omit tail frames unless the required final state needs one; overconstrained identical start/end frames can erase the action.
4. Use the quickest suitable model declared by current Kling capabilities. Do not assume a fixed model, duration or fee. Reserve, submit once, save each generation ID immediately, poll existing tasks and download. Independent jobs may overlap only within provider/account concurrency limits; default serial submission is safer than guessing limits. Keep project checkpoints while jobs run. No automatic paid retry on failures or disappointing output.
5. Review actual motion, not just attractive first frames. Check hands, face, product geometry and object permanence where relevant. A 30-second sample still needs all its selected intervals checked. Prefer a clean source subrange and a truthful shorter action over another generation only when the requested length and meaning remain intact. Record accepted ranges and hashes; disclose retiming. If an essential action is absent, report a blocker and ask about a focused retry, do not hide it with fast cuts.
6. Assemble the exact-length MP4 with rhythmically motivated cuts and continuous authorized audio. Preserve natural sound if useful; avoid layering several generated music beds. Add exact text in post. Run technical QA, inspect the real first/last frames and every cut, and listen if possible. Provide the MP4 and cover first, plus a one-line concept, duration and actual/estimated credits. Keep prompts, receipts and the manifest saved; don't make the user read them to watch the result.

## Budget and stopping rules

Quick mode means fewer decisions and fewer assets, not bypassed payment or external-upload authorization. Follow existing user scope and the provider contract. Consolidate missing setup/permission questions once. Never recharge, purchase a subscription, change model intent or regenerate a paid failure automatically. If no video provider is connected, say which dependency is missing and retain the prepared project; don't present still-frame motion as a completed Kling sample.

Use `scripts/video_pipeline.py` for `doctor`, `init`, `validate`, `reserve`, `record`, `assemble`, `qa` and `frames`. The helper never calls imagegen or Kling itself. Samples are complete only when actual exported video and required audio exist and the stated QA is done.
