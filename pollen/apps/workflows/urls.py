from django.urls import path

from pollen.apps.workflows import views

urlpatterns = [
    path("login/", views.console_login, name="console-login"),
    path("logout/", views.console_logout, name="console-logout"),
    path("", views.console_dashboard, name="console-dashboard"),
    path("templates/", views.template_manager, name="console-templates"),
    path("templates/<int:pk>/delete/", views.template_delete, name="console-template-delete"),
    path("schedules/", views.schedule_manager, name="console-schedules"),
    path("schedules/<int:pk>/delete/", views.schedule_delete, name="console-schedule-delete"),
    path("runs/", views.run_manager, name="console-runs"),
    path("runs/<int:pk>/resume/", views.run_resume, name="console-run-resume"),
    path("runs/<int:pk>/refresh/", views.run_refresh, name="console-run-refresh"),
    path("publications/", views.publication_manager, name="console-publications"),
    path("publications/<int:pk>/publish/", views.publish_run, name="console-publish-run"),
]
