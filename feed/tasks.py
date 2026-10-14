import logging
import os
import subprocess

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from django.core.files import File

from .models import PostVideo, Post

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, soft_time_limit=280)
# bind=True      -> gives us `self`, needed for self.retry() and self.request.retries
# max_retries=2  -> after the first failure, retry up to 2 more times (3 attempts total)
# soft_time_limit=280 -> Celery raises an exception inside the task after 280 seconds
def transcode_and_attach_video(self, post_video_id, tmp_path):
    # Load the PostVideo row created in the serializer (status is "processing")
    post_video = PostVideo.objects.get(id=post_video_id)

    # Output goes next to the raw file: "abc_raw.mov" -> "abc_raw_compressed.mp4"
    # Built from the path itself, so it can never equal the input path
    output_path = f"{os.path.splitext(tmp_path)[0]}_compressed.mp4"

    try:
        subprocess.run(
            [
                "/usr/bin/ffmpeg",
                "-y",                    # overwrite the output file if it exists
                "-i", tmp_path,          # input: the raw upload saved on disk

                # Pick streams explicitly:
                "-map", "0:v:0",         # first video stream of input 0
                "-map", "0:a:0?",        # first audio stream; the "?" means
                                         # "optional", so silent videos don't fail

                # Video: shrink if wider than 1920px, keep aspect ratio
                # -2 makes the height divisible by 2, which H.264 requires
                "-vf", "scale='min(1920,iw)':-2",

                # Video codec and quality
                "-c:v", "libx264",       # H.264, plays on every phone
                "-crf", "28",            # quality: lower = better and bigger (18-28 typical)
                "-preset", "veryfast",   # encoding speed vs. file size trade-off
                "-pix_fmt", "yuv420p",   # most compatible color format; avoids
                                         # playback problems with 10-bit/HDR phone video

                # Audio codec: original audio re-encoded to AAC at 128 kbps
                "-c:a", "aac", "-b:a", "128k",

                # Move metadata to the start of the file so playback can begin
                # before the whole file has downloaded
                "-movflags", "+faststart",

                output_path,
            ],
            check=True,              # raise CalledProcessError if ffmpeg exits with an error
            capture_output=True,     # keep ffmpeg's output so we can log it on failure
            timeout=270,             # kill the ffmpeg process itself if it runs too long
                                     # (soft_time_limit alone could leave it running)
        )

        # Upload the compressed file to storage (Cloudinary)
        with open(output_path, "rb") as f:
            post_video.video.save(f"{post_video_id}.mp4", File(f), save=False)
        post_video.processing_status = "done"   # the app polls this value
        post_video.save()

        # Success: now it's safe to delete both temp files
        for p in (tmp_path, output_path):
            if os.path.exists(p):
                os.remove(p)

    except Exception as exc:
        # Log ffmpeg's last error lines so failures can be diagnosed
        if isinstance(exc, subprocess.CalledProcessError):
            logger.error("ffmpeg failed for %s: %s", post_video_id,
                         (exc.stderr or b"")[-1500:].decode(errors="ignore"))

        # Remove a possibly half-written output, but KEEP tmp_path:
        # a retry needs the raw upload to still exist
        if os.path.exists(output_path):
            os.remove(output_path)

        try:
            # Retry after 10s, then 20s. self.retry() raises, so the code below
            # only runs once retries are used up
            raise self.retry(exc=exc, countdown=10 * (self.request.retries + 1))
        except MaxRetriesExceededError:
            # Out of attempts: mark failed and clean up the raw upload
            post_video.processing_status = "failed"
            post_video.save()
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            # Delete the post shortly after (the delay lets the app see "failed" first)
            delete_failed_post.apply_async(args=[str(post_video.post_id)], countdown=60)


@shared_task
def delete_failed_post(post_id):
    # Re-check the status before deleting, in case something fixed it meanwhile
    Post.objects.filter(id=post_id, videos__processing_status="failed").delete()