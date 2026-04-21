from django.urls import path

from pollen.apps.core.views import home

urlpatterns = [
    path("", home, name="home"),
]
