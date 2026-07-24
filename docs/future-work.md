# Future Work — Ready-to-Start Design Notes

This file holds detailed, "pick up and go" design plans for features that
were investigated but deliberately **not implemented** because they need
their own approval/plan round (per user decisions logged in `PROGRESS.md`).
Nothing here is implemented. No code in this repo depends on this document.

Written during the `overnight/launch-readiness` session (GÖREV D) so a
future session — with or without full context of `PROGRESS.md`'s history —
can start productively without re-deriving the architecture questions from
scratch.

---

## 1. Podcast (audio-only) support

### Why this doesn't work today (verified in code, not guessed)

- `app/pipeline/default_pipeline.py` runs a fixed 12-stage sequence with
  **no stage marked skippable**. There is no `if audio_only:` branch
  anywhere in the pipeline.
- The final two post-stage-12 steps assume a rendered video unconditionally:
  `thumbnail_generator.generate_thumbnail(project.timeline.combined_video_path, ...)`
  reads `project.timeline.combined_video_path` with **no None-check** — if
  `project.timeline` were ever `None` (as it would be if the video-specific
  stages were skipped), this is a bare `AttributeError`, not a handled case.
- `app/departments/production/video_renderer.py`'s `render_final_video()`
  takes a `timeline: Timeline` as a **required** argument — there's no
  audio-only rendering path in the legacy `video.py` it wraps either.
- `app/models/documentary_project.py`'s `DocumentaryProject.final_video_path: str`
  is the pipeline's **only** notion of a finished deliverable. There is no
  `final_audio_path` field, and nothing else in the model represents "this
  project's output is an audio file, not a video file."
- `app/departments/growth/seo_generator.py`'s own docstring says outputs are
  sized for "short vertical video (Shorts/TikTok/Reels)" — the SEO prompt
  itself (`app/services/llm.py`'s `generate_social_metadata`) is tuned for
  video platforms, not podcast directories (Spotify/Apple Podcasts have
  different metadata conventions: episode show notes, no vertical thumbnail
  concept, no hashtags-as-primary-discovery).
- `app/departments/production/asset_downloader.py` / `asset_generator.py`
  fetch stock **video** footage unconditionally — for a podcast there is
  nothing to show, so this entire stage (and its real Pexels API cost)
  would be pure waste if run for an audio-only project.

### Two honest architecture options (pick one — this is the actual decision this needs)

**Option A — Parallel pipeline function (`run_audio_pipeline()`)**

A new function in `default_pipeline.py` (or a new `app/pipeline/audio_pipeline.py`)
that reuses the text/research/script stages (intent → research → outline →
scene → script are 100% video-agnostic already) but **skips** storyboard,
asset, asset-download, and calls `audio_renderer.render_narration()` directly
as the deliverable, with a new SEO variant for podcast metadata.

- Pros: no risk to the existing video pipeline at all (it's untouched);
  the audio-only path can evolve independently.
- Cons: duplicates ~5 lines of orchestration logic; two pipelines to keep
  in sync if a shared stage (e.g. script_generator) changes behavior.

**Option B — `output_mode: Literal["video", "audio"]` parameter on `run_pipeline()`**

Add a mode flag; branch internally around storyboard/asset/timeline/video-render;
add `DocumentaryProject.final_audio_path: str = ""` alongside (not replacing)
`final_video_path`; make `thumbnail_generator`/`quality_critic`/webui checks
None-safe for a missing `project.timeline`.

- Pros: one pipeline, one mental model, one set of tests to maintain long-term.
- Cons: `default_pipeline.py`'s `run_pipeline()` gets meaningfully more
  branching (stage(7) through stage(12) all become conditional), touching
  the same core file GÖREV 1 just hardened — higher regression surface on
  the pipeline every future session touches.

**Recommendation (not a decision — the user should make this call):** Option A
is safer short-term (isolated, reversible, doesn't touch the video pipeline's
proven code path) at the cost of a small amount of duplication. Option B is
the "correct" long-term shape if podcast support is expected to be a
first-class, permanently-maintained feature rather than an experiment.

### Concrete step list (once the option above is chosen)

1. Add `AudioTrack`-only "deliverable" concept: either `final_audio_path`
   on `DocumentaryProject` (Option B) or a separate lightweight
   `PodcastProject` model (Option A) — decide based on the option chosen.
2. New SEO variant: `seo_generator.generate_podcast_metadata()` (episode
   title, show notes/description, no hashtags-as-discovery emphasis) —
   can reuse `llm.generate_social_metadata(platform=...)`'s existing
   platform-conditional prompt building if a `"podcast"` platform branch
   is added there, or a fully separate prompt if podcast metadata
   conventions differ enough (episode numbering, guest names, timestamps
   linked to `seo_generator.generate_chapters()` — which, unlike for
   Shorts, **would actually be functional** for a podcast episode; this is
   the one place `chapters` stops being purely advisory).
3. Skip `storyboard_generator` → `asset_generator` → `asset_downloader` →
   `timeline_builder` → `video_renderer` entirely for the audio path; the
   deliverable is `audio_renderer.render_narration()`'s output directly
   (already produces a real `audio.mp3` + `subtitle.srt` today, mid-pipeline —
   confirms the audio stage itself needs zero new code).
4. webui: a new "Podcast" mode toggle/tab; None-guard every place that
   currently assumes `project.timeline`/`project.final_video_path` exists
   (search `webui/Main.py` for `final_video_path` and `thumbnail_path` reads —
   both currently assume truthy-checked but present fields).
5. `thumbnail_generator` either skipped entirely for audio-only projects, or
   (nice-to-have, not required) generate a static "podcast cover" using only
   the SEO title over a solid/branded background (no video frame available)
   — this is new, not a reuse of existing frame-extraction code.
6. Real verification plan: run the audio pipeline end-to-end for one real
   topic, confirm `audio.mp3` + `subtitle.srt` are produced, confirm the
   *video* pipeline's existing tests still pass unmodified (proves no
   regression), confirm webui doesn't crash when `project.timeline is None`.

### Testing approach
Mirror `test_default_pipeline.py`'s full-mock wiring test style, but for
whichever new function/branch is added — assert stages actually skipped
(asset_downloader.download_assets, video_renderer.render_final_video)
are never called for an audio-only run, exactly like the existing test
asserts `thumbnail_b` is never called when variant A fails.

---

## 2. Kids / age-appropriate content mode

### Why this doesn't work today (verified in code, not guessed)

- A full-repo search for `moderation`, `age_appropriate`, `content_filter`,
  `nsfw`, `profanity` (case-insensitive, across `app/`) returns **zero
  results**. There is no content-safety mechanism anywhere in this
  codebase today — not a stub, not a TODO, nothing.
- `app/thinking/quality_critic.py`'s `QualityVerdict` model
  (`app/models/quality.py`) scores `coherence_score` / `pacing_fit_score` /
  `seo_quality_score` only — there is no `age_appropriateness_score` or
  equivalent, and the LLM prompt behind it (whatever generates the verdict)
  is never told to evaluate for child-safety at all.
- A "simplified language" Format-style instruction (the same pattern used
  for `Format.educational`/`Format.corporate`) would change **vocabulary
  level**, not **content safety** — these are orthogonal. A simplified-language
  documentary about, say, a violent historical event would still be
  simplified but not safe for young children. Conflating the two would be
  a real product-safety risk if shipped as "Kids mode."

### What "done right" actually requires (this is the real scope, not a small feature)

This is fundamentally different in kind from Podcast (an engineering/plumbing
problem) — Kids mode is a **content-safety product decision** with real-world
stakes if it fails silently. A minimal responsible version needs, at minimum:

1. **A topic-level pre-filter**, before any generation starts: reject or
   flag topics unsuitable for children regardless of how "simply" they'd be
   narrated (violence, death, disasters, mature historical events — many of
   this app's own example topics like "The Fall of Rome" or "The Berlin Wall"
   involve war/death and would need a judgment call on this filter).
2. **A content-level check on generated output**, after script generation —
   an explicit LLM-as-judge pass (similar in shape to `quality_critic`, but
   for a different question: "would a parent be comfortable with a 6-10
   year old watching/hearing this narration") — this cannot be inferred from
   the existing `quality_critic` scores, which measure narrative quality,
   not safety.
3. **A documented, explicit failure mode**: what happens when a topic or
   generated script fails the safety check? Silently regenerate with a
   stricter prompt? Refuse and tell the user why? Fall back to a
   pre-approved topic list? This needs an actual product decision, not an
   engineering default.
4. **Explicit non-goals stated up front**: this cannot be marketed or
   treated as a *guarantee* of child safety — LLM content-safety judgment is
   itself imperfect. Any "Kids mode" needs a visible disclaimer in the UI
   (e.g., "AI-generated; please preview before sharing with children") so
   the product doesn't imply a certification it can't back up.

### Concrete step list (once the above product decisions are made)

1. New `app/thinking/kids_safety_critic.py` (mirroring `quality_critic.py`'s
   shape: `evaluate_topic(topic) -> TopicSafetyVerdict` pre-check, and
   `evaluate_script(script) -> ContentSafetyVerdict` post-check) — two
   separate functions since topic-level and content-level checks answer
   different questions and can fail independently.
2. New models: `TopicSafetyVerdict` (`safe: bool`, `reason: str`) and
   `ContentSafetyVerdict` (`safe: bool`, `concerns: list[str]`) in
   `app/models/quality.py` or a new `app/models/safety.py`.
3. Pipeline integration point: topic-level check right after stage 1
   (intent) — cheap to fail fast before spending any more LLM/API budget;
   content-level check right after stage 5 (script) — before any paid
   asset-download/TTS calls are made on content that might get rejected.
4. `default_pipeline.py` needs an explicit decision on what a failed check
   *does*: raise (matching this pipeline's existing "hard stop on real
   failure" pattern for e.g. `render_narration`'s `RuntimeError`), or return
   a project with a `blocked: bool` / `block_reason: str` field the webui
   surfaces clearly instead of a video. Recommend the latter — silently
   crashing to a generic error is a worse UX for a rejected-for-safety case
   than a clear, specific message.
5. `Format.kids` (parallel to today's `Format.educational`/`Format.corporate`)
   for the vocabulary-simplification part **only**, added *after* the safety
   layer exists — never ship simplified-vocabulary-only as "Kids mode" on
   its own, since that's the exact conflation flagged as a risk above.
6. webui: a visible, un-dismissable disclaimer whenever Kids mode is
   selected (see non-goal #4 above) + a clear "blocked" state distinct from
   a normal generation-failed error.

### Testing approach
Given this is safety-critical, testing needs to go beyond the usual
mock-the-LLM-call pattern: a curated test set of topics that **should** pass
and topics that **should** be blocked (edge cases: historical topics with
mature elements, ambiguous topics), run against the real safety-critic
prompt (not mocked) periodically to catch prompt-drift regressions — a
pure mock test would only prove the code calls the LLM, not that the LLM's
judgment is still calibrated correctly.

### Explicit recommendation
**Do not build the vocabulary-only version and call it "Kids mode."** If a
future session is under time pressure and only Format.kids (Format.educational's
sibling) gets built without the safety layer, it must be named and documented
as what it actually is — a *reading-level* format, not a child-safety feature —
to avoid the product implying a safety guarantee it doesn't have.

---

## 3. Analytics / Learning Layer (brief note, lower detail — genuinely blocked on real data)

Already covered in `PROGRESS.md`'s original Phase 2 plan: this layer needs
real published-video performance data (views, engagement) to train any
topic/prompt-selection feedback loop. The Publishing Engine (`app/departments/growth/publisher.py`)
now exists and could theoretically start collecting outcome data, but:

- No analytics-fetching integration exists yet (would need each platform's
  own API: YouTube Data API for view/engagement counts, TikTok/Instagram
  equivalents) — this is itself a decent-sized new integration, not free.
- Zero real publish events have happened yet in this project's history
  (Publishing Engine has only been verified with mocks + a config-validity
  check, per its own PROGRESS.md entry) — building a learning loop on zero
  data points is premature regardless of engineering readiness.

**Recommendation: revisit this only after the user has actually published
a handful of real videos** and wants to close the loop — not before. No
further design detail is written here since the actual data shape this
layer would need depends entirely on what each platform's analytics API
returns, which isn't worth speculating about in the abstract.
