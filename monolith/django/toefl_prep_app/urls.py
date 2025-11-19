# toefl_prep_app/urls.py

from django.urls import path
from .views import profile, test_page
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('profile/', profile, name='profile'),
    path('test/<int:question_id>/', test_page, name='test_page'),
    path('logout/', views.custom_logout, name='logout'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    # Add more URLs as needed
]
