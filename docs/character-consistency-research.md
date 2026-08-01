# Character Consistency Research — AI Video Models

**Status: research only. No pipeline integration. Nothing in this repo
depends on this document or reads `resource/characters/`.** Written to
support a supervised planning session (not this one) on whether/how to add
character-consistent video generation (e.g. for an educational kids-cartoon
format) — see `PROGRESS.md` for the request context.

**Question asked:** which AI video generation models accept a REFERENCE
IMAGE (an uploaded character photo/drawing) via their API and can generate
that same character, consistently, in different scenes/poses?

**Short answer:** none of the three models currently integrated in this
project (`app/services/fal_video.py`: Kling v1 standard, Hailuo, Veo 3.1)
support this. All three only accept a single "start frame" image at best.
A **different, not-yet-integrated** Kling variant on fal.ai —
**`fal-ai/kling-video/o1/standard/reference-to-video`** (and a newer `o3`
sibling) — does support real, multi-image character-reference consistency,
and a real, live test (below) confirms it actually works well.

## Methodology

1. Read the actual images in `resource/characters/` to know what's being
   tested (see "The four characters" below).
2. For every model, pulled the **live OpenAPI schema** directly from
   `https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=<model>`
   rather than trusting marketing pages or memory — this is fal.ai's own
   machine-readable, authoritative parameter list for that exact model
   version. (fal.ai's regular marketing/docs pages return HTTP 429 to
   automated fetches; this OpenAPI JSON endpoint does not.)
3. Searched fal.ai's broader catalog for any other dedicated
   "consistent character" offering, video or otherwise.
4. Ran exactly one real, paid API call end-to-end against the single most
   promising model, using one of the four real reference characters, and
   visually inspected the actual resulting video frames.

## The four characters

`resource/characters/` contains 4 JPEG files, each a 3-view (front /
three-quarter / back) character reference sheet, 1376×768, generated
outside this project (not by any code here):

| File | Character |
|---|---|
| `Tam_boy_üçlü,...202608011147.jpeg` | "civciv" — round, fluffy blue chick |
| `Tam_boy_üçlü,...202608011148 (1).jpeg` | "baykuş" — owl, glasses + leather satchel |
| `Tam_boy_üçlü,...202608011148.jpeg` | "panda" — panda, yellow woven vest + backpack, holding bamboo |
| `am_boy_üçlü,...202608011148.jpeg` | "mavi kuş" — slender, Disney-style blue bird, labeled "Front/Three-Quarter/Back View" |

(The 4th filename's leading "T" is missing — cosmetic upload artifact,
confirmed harmless, per the user's own note.)

## Per-model findings (from fal.ai's live OpenAPI schemas)

### Kling — currently integrated model (`fal-ai/kling-video/v1/standard/image-to-video`)

This is what `app/services/fal_video.py`'s `_build_kling_payload()` uses
today. Real schema fields: `image_url` (single start frame),
`tail_image_url` (optional end frame), `dynamic_masks`/`static_mask_url`
(motion-brush regions), `prompt`, `negative_prompt`, `cfg_scale`,
`duration`. **No reference-image or character/element concept at all.**
Feeding it a character sheet would only ever use it as a single starting
frame — no mechanism to say "keep this character's identity."

### Kling O1 / O3 Reference-to-Video — NOT currently integrated

`fal-ai/kling-video/o1/standard/reference-to-video` (internal model name:
`OmniVideoReferenceToVideoInput`). Real schema, quoted directly from the
live OpenAPI JSON:

```json
{
  "prompt": "string, required, max 2500 chars — 'Take @Element1, @Element2 to reference elements and @Image1, @Image2 to reference images in order.'",
  "image_urls": "array of image URLs — 'Additional reference images for style/appearance. Reference in prompt as @Image1, @Image2, etc.'",
  "elements": [
    {
      "frontal_image_url": "string, required — the main/front view of a character or object",
      "reference_image_urls": "array of 1-3 additional images — 'Additional reference images from different angles.'"
    }
  ],
  "duration": "enum '3'..'10' seconds, default '5'",
  "aspect_ratio": "enum '16:9' | '9:16' | '1:1', default '16:9'"
}
```

Key constraint: **max 7 total** (`elements` + `image_urls` + the implicit
start frame) per request. Each `elements` entry maps almost perfectly onto
our 3-view reference sheets: `frontal_image_url` = front view,
`reference_image_urls` = [three-quarter, back]. In the prompt you address
a specific character as `@Element1`, `@Element2`, etc., and a specific
plain reference image as `@Image1`, `@Image2`, etc.

`fal-ai/kling-video/o3/standard/reference-to-video` is a newer sibling
(`about: "O3 Std Reference To Video"`) with the same `elements` concept
plus extras: `start_image_url`/`end_image_url` (first/last frame control
combined with character elements), `multi_prompt`/`shot_type` (multi-shot
generation in one request), native `generate_audio`, and a longer
3–15s `duration` range. Not tested live tonight (scope was one real test,
spent on O1) but worth evaluating first in any future follow-up, since it
appears to be a strict superset of O1's capability.

**Pricing (real, found via search, not the OpenAPI schema which doesn't
carry price):** Kling O1 Reference-to-Video is **$0.112/s** — a 5s clip is
$0.56, a 10s clip $1.12. For comparison, this project's current default
(Kling v1 standard) runs ~$0.045/s, and Veo 3.1 Fast (already integrated
for the "AI Üretimi" page) runs ~$0.10/s — so character-consistent
generation costs roughly **2.5x** today's Kling default, in the same
ballpark as Veo.

### Hailuo (`fal-ai/minimax/hailuo-02/standard`) — currently integrated

`text-to-video` variant: `prompt`, `prompt_optimizer`, `duration` — no
image input of any kind. `image-to-video` variant: `image_url` (single
start frame) + optional `end_image_url` (single last frame). **No
reference/element/character concept.** Same conclusion as Kling v1: only
usable as a single starting frame, not real character consistency. (This
project already knows Hailuo doesn't even support 9:16 output — see
`PROGRESS.md` ADIM 3 — making it doubly unsuitable here.)

### Google Veo 3.1 / 3.1 Fast — currently integrated

Checked all 4 real variants: `veo3.1`, `veo3.1/fast` (pure text-to-video,
no image field at all) and `veo3.1/image-to-video`,
`veo3.1/fast/image-to-video` (single `image_url` — "URL of the input image
to animate"). **No reference-image, multi-image, or character/element
concept in any Veo 3.1 endpoint.** Same single-start-frame ceiling as
Kling v1 and Hailuo.

## Broader fal.ai catalog: dedicated "consistent character" models exist — but they're image-to-image, not video

Search turned up real, dedicated character-consistency models on fal.ai,
but all in a **different product category** (still images, not video):

- `fal-ai/ideogram/character` — "Generates consistent character appearances
  across multiple images, maintaining facial features, proportions, and
  distinctive traits" (+ `/remix`, `/edit` variants for restyling a
  consistent character).
- `fal-ai/instant-character` — "Creates high-quality, consistent characters
  from text prompts, supporting diverse poses, styles, and appearances."
- `fal-ai/minimax/image-01/subject-reference` — generates a new still image
  from a text prompt + one reference image, for consistent character
  appearance.

These could theoretically feed a **different** pipeline shape (generate a
consistent still frame first, then animate it with a plain image-to-video
model), but that's a materially different, two-stage architecture from
what's asked here, and wasn't tested. For a single-step "reference in,
consistent video out" answer, Kling O1/O3 Reference-to-Video is the real,
current answer among everything checked.

## Real API test (paid, real money spent — $0.56)

**Setup:** the panda reference sheet was cropped (via PIL, a one-off local
image edit, not a pipeline change) into 3 separate images — front,
three-quarter, back — since `elements` needs individual image URLs/data,
not one combined triptych. Sent as base64 `data:image/jpeg;base64,...`
URIs directly in the JSON payload (fal.ai's documented alternative to a
separate upload step, fine for small one-off test images).

**Real request sent** to `fal-ai/kling-video/o1/standard/reference-to-video`:

```json
{
  "prompt": "Take @Element1. The exact same panda character, wearing its yellow woven vest and backpack, is now walking through a sunny bamboo forest, looking around curiously, then turns to face the camera and waves one paw. Cinematic lighting, warm and cheerful mood.",
  "elements": [{"frontal_image_url": "<panda front, base64>", "reference_image_urls": ["<panda 3/4, base64>", "<panda back, base64>"]}],
  "duration": "5",
  "aspect_ratio": "9:16"
}
```

**Result:** real HTTP 200, real render (queued → in-progress → completed in
~2 minutes), real downloaded `output.mp4` — **ffprobe-confirmed 720×1280
(9:16), 5.04s, h264**, $0.56 billed. Two representative frames, saved
alongside this report:

- [`character-consistency-test/reference_input_front.jpg`](character-consistency-test/reference_input_front.jpg) — the input.
- [`character-consistency-test/result_frame_walking.jpg`](character-consistency-test/result_frame_walking.jpg) — panda walking through a bamboo forest.
- [`character-consistency-test/result_frame_waving.jpg`](character-consistency-test/result_frame_waving.jpg) — panda turned to camera, waving, exactly as the prompt asked.

**Visual assessment (real, not assumed):** the output panda is clearly and
consistently the *same* character in every inspected frame — same face
shape and markings, same yellow woven vest, same woven backpack with its
distinctive side bottle-pockets, same round body proportions — in a
brand-new scene (bamboo forest) and a brand-new pose/action (walking, then
turning and waving) that appear in none of the 3 reference images. The
model also correctly followed the specific action instructions in the
prompt (turn to camera, wave one paw). This is a genuine, working
character-consistency result, not a coincidental resemblance.

## Bottom line for the planning session

- **Not usable today:** none of the 3 models this project already talks to
  (Kling v1, Hailuo, Veo 3.1) can do this — swapping in a reference image
  only ever gives you a single start frame, never identity preservation.
- **Real, working option found:** `fal-ai/kling-video/o1/standard/reference-to-video`
  (and its newer `o3` sibling, untested but likely stronger — multi-shot,
  native audio, start+end frame, same `elements` mechanism). Confirmed
  live: accepts our exact 3-view reference-sheet shape via
  `frontal_image_url` + `reference_image_urls`, supports 9:16, and
  genuinely preserves character identity across a brand-new scene/pose.
- **Cost:** ~2.5x this project's current Kling default (~$0.045/s vs
  $0.112/s) — a real, ongoing cost consideration for a Kids-format feature
  that would presumably generate many short clips per episode.
- **Not decided here:** whether to build on O1 or O3, how `elements` would
  be threaded through `default_pipeline.py`/`asset_generator.py` (today's
  pipeline has no concept of a fixed cross-scene character asset at all),
  whether the 3-crop-from-one-sheet approach used in this test is the
  right long-term asset format, or how this interacts with the existing
  Kling/Hailuo/Veo provider-selection pattern in `fal_video.py`. All of
  that is real design work for the supervised session this report is
  feeding into — intentionally not started here.
