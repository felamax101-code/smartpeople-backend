from django.contrib import admin

from .models import ProfilePrivacy

@admin.register(ProfilePrivacy)
class ProfilePrivacyAdmin(admin.ModelAdmin):
    list_display = ("user", "show_phone", "show_email", "show_location", "show_followers", "show_following", "who_can_message", "who_can_follow", "show_online_status")
    search_fields = ("user__username",)
    list_filter = ("who_can_message", "who_can_follow")
