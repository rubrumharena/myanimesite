"""
URL configuration for myanimesite project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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

import debug_toolbar
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from subscriptions.views import stripe_webhook_view
from titles.views import IndexView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', IndexView.as_view(), name='index'),
    path('', include('titles.urls', namespace='titles')),
    path('', include('users.urls', namespace='users')),
    path('lists/', include('lists.urls', namespace='lists')),
    path('comments/', include('comments.urls', namespace='comments')),
    path('accounts/', include('allauth.urls')),
    path('auth/', include('accounts.urls')),
    path('video_player/', include('video_player.urls')),
    path('subscriptions/', include('subscriptions.urls', namespace='subscriptions')),
    path('webhook/stripe/', stripe_webhook_view, name='stripe_webhook'),
]

if settings.DEBUG:
    urlpatterns.append(path('__debug__/', include(debug_toolbar.urls)))
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
