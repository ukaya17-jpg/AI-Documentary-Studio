"""Growth stage: publish the finished documentary to social platforms via the
existing app.services.upload_post (Upload-Post.com relay) integration.

Unlike every other stage, this is never called from
app.pipeline.default_pipeline.run_pipeline() -- publishing is a public,
hard-to-reverse action, so it's only triggered explicitly by the user (see
webui's Publish section) after they've reviewed final_video_path/thumbnail/seo,
not run automatically as a best-effort pipeline step like thumbnail
generation.
"""

from datetime import datetime, timezone

from app.models.documentary_project import DocumentaryProject
from app.models.publish import PublishResult
from app.services import upload_post


def publish_project(
    project: DocumentaryProject,
    platforms: list[str] | None = None,
    youtube_privacy_status: str | None = None,
) -> PublishResult:
    """Cross-post project.final_video_path (+ SEO title/description/hashtags)
    to `platforms`, defaulting to the configured upload_post_platforms.

    `youtube_privacy_status` overrides the configured default for this call
    only -- it's passed through rather than written onto the shared
    upload_post_service singleton, since that singleton is also read by the
    legacy task.py cross-post flow and must not be mutated by a one-off
    webui selection.

    Returns a PublishResult describing what happened; never raises. Does not
    mutate `project` -- the caller decides whether/how to persist the result
    (see webui, which stores it in session state).
    """
    resolved_platforms = platforms if platforms is not None else list(upload_post.upload_post_service.platforms)

    if not upload_post.upload_post_service.is_configured():
        return PublishResult(
            success=False,
            error="Upload-Post is not configured",
            platforms=resolved_platforms,
        )

    if not project.final_video_path:
        return PublishResult(
            success=False,
            error="No final video to publish",
            platforms=resolved_platforms,
        )

    seo = project.seo
    title = seo.title if seo and seo.title else project.topic
    description = seo.description if seo else ""
    hashtags = list(seo.hashtags) if seo else []

    youtube_extra = None
    if any(p.startswith("youtube") for p in resolved_platforms):
        youtube_extra = {
            "youtube_title": title,
            "youtube_description": description,
            "tags": hashtags,
            "privacyStatus": youtube_privacy_status or upload_post.upload_post_service.youtube_privacy_status,
        }

    result = upload_post.cross_post_video(
        video_path=project.final_video_path,
        title=title,
        platforms=resolved_platforms,
        youtube_extra=youtube_extra,
    )

    return PublishResult(
        success=bool(result.get("success")),
        request_id=str(result.get("request_id", "")),
        error=str(result.get("error") or result.get("message") or ""),
        platforms=resolved_platforms,
        published_at=datetime.now(timezone.utc).isoformat(),
    )
