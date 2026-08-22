from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_home, name='dashboard_home'),
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]
