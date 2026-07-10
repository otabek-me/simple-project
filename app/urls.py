from django.urls import path
from . import views

urlpatterns = [
    path('', views.furniture_list, name='furniture_list'),
    path('mebel/yangi/', views.furniture_create, name='furniture_create'),
    path('mebel/<int:pk>/tahrir/', views.furniture_edit, name='furniture_edit'),
    path('mebel/<int:pk>/ochirish/', views.furniture_delete, name='furniture_delete'),
    path('detallar/', views.detail_list, name='detail_list'),
    path('detallar/<int:pk>/tahrir/', views.detail_edit, name='detail_edit'),
    path('detallar/<int:pk>/ochirish/', views.detail_delete, name='detail_delete'),
]
