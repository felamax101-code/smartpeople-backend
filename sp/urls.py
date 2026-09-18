"""
URL configuration for sp project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/",include("authentication.urls")),
    path("api/",include("feed.urls")),
    path("api/",include("Profile.urls")),
    path("api/groups/",include("groups.urls")),
    path("api/sp/",include("realestate.urls")),
    path("messaging/",include("messaging.urls")),
] + static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)
