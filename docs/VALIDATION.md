# Validation and release boundaries

## What is tested

The automated suite checks authored timelines, the 30-second quick-mode bound, positive frame counts, missing prompts, subtitle overlap, project path containment, audio constraints, Unicode file handling and exclusive project writes. The job-ledger tests cover missing authorization, a missing/insufficient budget, unknown outcomes, duplicate pending attempts, authorized retries, immutable provider IDs, terminal state preservation, and the difference between estimated charges, actual charges and refunds.

Integration tests use FFmpeg-generated test patterns and sine waves, **not paid AI outputs**. They export a real short MP4 with Chinese-path input, burned Chinese/English captions, source audio, separate voice/music channels, ducking, normalization, a cover and SRT. They verify actual exported frame count, dimensions, frame rate, decode and audio, source-hash invalidation, unreviewed source range rejection and refusing to overwrite a final.

`tools/check_bundle.py` verifies the two skill folders contain matching helper/reference copies, working local documentation links and valid invocation metadata. The skill-creator frontmatter validator is also run at release time when available in the development host.

## What is not tested or promised

- No new paid Kling jobs or native image generation were submitted solely for this release.
- The full end-to-end agent workflow has not been independently validated with a fresh paid production after packaging. The production decisions are distilled from prior work; the executable local pipeline has synthetic integration coverage.
- A runtime `technical_pass` never means the script watched the story, verified craft technique, listened to speech or checked media rights.
- No guarantee of a fixed queue time, exact generation cost before the provider reports it, universal model availability, seamless lip sync, perfect hands or exact textile patterns.
- Provider and host schemas can change. Discover them live and follow their applicable requirements.
- Cross-platform implementation uses Python standard library and subprocess argument arrays. Initial local release validation runs on Windows; GitHub Actions supplies an additional Linux check. A configured workflow alone is not evidence that the remote check passed.

## Scenario acceptance checks for the agent

| Request / situation | Required behavior |
|---|---|
| One sentence, no images, quick mode | Infer a direction and make a 15-second plan; no multi-round creative interview |
| A 45-second request to the quick skill | Explain the 30-second limit; offer the full skill, don't silently shorten |
| User uploads a reference face and costume | Inspect and label roles, preserve identity, verify required external-upload scope |
| A shot returns COMPLETED but a tool disappears midway | Reject bad source interval; do not mark it accepted from status alone |
| Paid call returned but response wasn't saved | Recover task ID and receipt before any further submission |
| No usable speech provider but narration is essential | Save the prepared project and identify BLOCKED_SOUND; don't quietly export a silent replacement |
| User asks for a new dress only | Preserve actor, scene, camera and unrelated props; invalidate affected downstream review |
| A 7-second insert replaces a 10-second insert | Recompute subsequent time offsets and audio edits; don't claim copied-audio hashes after re-encoding |

These scenario checks are documented acceptance criteria, not claims of a separate autonomous evaluator run.
