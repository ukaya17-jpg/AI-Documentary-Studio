"""Thinking Layer: LLM-as-judge quality review of a completed documentary project.

Standalone and non-blocking: not wired into
`app.pipeline.default_pipeline.run_pipeline()` as a mandatory stage. What
should happen on a failing verdict (stop the pipeline? retry a stage? just
warn?) is a separate, larger decision deferred until there's real usage data
to inform it -- see PROGRESS.md. On LLM/parse failure this returns None and
logs a warning; it must never raise or block the caller.
"""

from loguru import logger

from app.models.documentary_project import DocumentaryProject
from app.models.quality import QUALITY_PASS_THRESHOLD, QualityVerdict
from app.services.documentary_llm_utils import generate_json

_MAX_RETRIES = 3


def build_quality_prompt(project: DocumentaryProject) -> str:
    outline_summary = ""
    if project.outline:
        sections = "\n".join(
            f"- {s.title}: {s.summary}" for s in project.outline.sections
        )
        outline_summary = (
            f"Outline hook: {project.outline.hook}\n{sections}\n"
            f"Closing: {project.outline.closing}"
        )

    script_text = project.script.full_text if project.script else ""

    seo_text = ""
    if project.seo:
        seo_text = f"Title: {project.seo.title}\nDescription: {project.seo.description}"

    return f"""You are a documentary quality reviewer. Evaluate the following completed
documentary project before publishing.

Topic: "{project.topic}"

{outline_summary}

Narration script:
{script_text}

SEO metadata:
{seo_text}

Rate each dimension from 1 (poor) to 5 (excellent):
- coherence_score: does the narration flow logically, with no unexplained references or contradictions?
- pacing_fit_score: does the narration's pacing feel appropriate for a short documentary (not rushed, not padded)?
- seo_quality_score: is the title/description specific, accurate, and likely to attract the right audience?

Respond with a single JSON object with exactly this shape:
{{"coherence_score": 1, "pacing_fit_score": 1, "seo_quality_score": 1, "issues": ["..."]}}
List concrete issues only if they exist (empty list is fine). Do not include any other text."""


def evaluate_project(project: DocumentaryProject) -> QualityVerdict | None:
    prompt = build_quality_prompt(project)
    try:
        data = generate_json(prompt, max_retries=_MAX_RETRIES)
        coherence = int(data["coherence_score"])
        pacing = int(data["pacing_fit_score"])
        seo = int(data["seo_quality_score"])
        for score in (coherence, pacing, seo):
            if not 1 <= score <= 5:
                raise ValueError(f"score out of range: {score}")

        overall = round((coherence + pacing + seo) / 3, 2)
        issues = [str(i).strip() for i in data.get("issues", []) if str(i).strip()]
        return QualityVerdict(
            coherence_score=coherence,
            pacing_fit_score=pacing,
            seo_quality_score=seo,
            overall_score=overall,
            passed=overall >= QUALITY_PASS_THRESHOLD,
            issues=issues,
        )
    except Exception as e:
        logger.warning(f"quality_critic: evaluation failed, skipping verdict: {e}")
        return None
