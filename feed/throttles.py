
from rest_framework.throttling import ScopedRateThrottle

class VideoStatusThrottle(ScopedRateThrottle):
    scope = "video_status"

from rest_framework.throttling import UserRateThrottle

class SoundUploadHourlyThrottle(UserRateThrottle):
    scope = "sound_upload_hour"

class SoundUploadDailyThrottle(UserRateThrottle):
    scope = "sound_upload_day"