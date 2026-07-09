from django.urls import path
from . import views

urlpatterns = [
    path('', views.furniture_list, name='furniture_list'),
    path('mebel/yangi/', views.furniture_create, name='furniture_create'),
    path('mebel/<int:pk>/tahrir/', views.furniture_edit, name='furniture_edit'),
]
