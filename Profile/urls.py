from django.urls import path

from .views import ProfilePrivacyView
urlpatterns=[
    path("users/me/privacy/", ProfilePrivacyView.as_view(), name="privacy-settings"),
]