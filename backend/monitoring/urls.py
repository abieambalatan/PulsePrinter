from django.urls import path

from . import views


urlpatterns = [
    path('health/', views.health),
    path('auth/csrf/', views.csrf_token),
    path('auth/login/', views.auth_login),
    path('auth/logout/', views.auth_logout),
    path('auth/me/', views.auth_me),
    path('auth/profile/', views.auth_profile_update),
    path('dashboard/', views.dashboard),
    path('printers/', views.printers),
    path('printers/sync/', views.sync_printers),
    path('printers/agent-sync/', views.agent_sync_printers),
    path('print-jobs/', views.print_jobs),
    path('print-jobs/ingest/', views.ingest_print_job),
    path('paper-usage/', views.paper_usage),
    path('alerts/', views.alerts),
    path('reports/summary/', views.report_summary),
    path('reports/export/', views.export_report),
]
