
import os
import subprocess
from celery import shared_task
from django.core.files import File
from django.core.files.storage import default_storage
from .models import PostVideo,Post

from celery.exceptions import MaxRetriesExceededError

@shared_task(bind=True, max_retries=2, soft_time_limit=280)
def transcode_and_attach_video(self, post_video_id, tmp_path):
    post_video = PostVideo.objects.get(id=post_video_id)
    output_path = tmp_path.replace("_raw", "_compressed").rsplit(".", 1)[0] + ".mp4"

    try:
        subprocess.run(
            [
                "/usr/bin/ffmpeg", "-y", "-i", tmp_path,
                "-vf", "scale='min(1920,iw)':-2",
                "-c:v", "libx264", "-crf", "28", "-preset", "veryfast",
                "-c:a", "aac", "-b:a", "128k",
                output_path,
            ],
            check=True, capture_output=True,
        )
        with open(output_path, "rb") as f:
            post_video.video.save(f"{post_video_id}.mp4", File(f), save=False)
        post_video.processing_status = "done"
        post_video.save()

        # only safe to delete the raw upload once we've actually succeeded
        for p in (tmp_path, output_path):
            if os.path.exists(p):
                os.remove(p)

    except Exception as exc:
        # clean up a possibly-partial compressed output, but keep the raw
        # upload — a retry needs tmp_path to still exist on disk
        if os.path.exists(output_path):
            os.remove(output_path)

        try:
            raise self.retry(exc=exc, countdown=10 * (self.request.retries + 1))
        except MaxRetriesExceededError:
            # genuinely out of attempts now — give up for real
            post_video.processing_status = "failed"
            post_video.save()
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            delete_failed_post.apply_async(args=[str(post_video.post_id)], countdown=60)


@shared_task
def delete_failed_post(post_id):
    # re-check the status before deleting — belt-and-suspenders in case
    # something else already fixed it in the meantime
    Post.objects.filter(id=post_id, videos__processing_status="failed").delete()
