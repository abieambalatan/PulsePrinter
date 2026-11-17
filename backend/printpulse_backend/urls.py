from django.contrib import admin
from django.urls import include, path
from monitoring import views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('monitoring.urls')),
    path('', views.frontend_app, name='frontend'),
    path('<path:path>', views.frontend_app, name='frontend-route'),
]
