from django.urls import path
from . import views

urlpatterns = [
    path('', views.furniture_list, name='furniture_list'),
    path('zahira/', views.reserve_list, name='reserve_list'),
    path('zahira/<int:pk>/tahrir/', views.reserve_edit, name='reserve_edit'),
    path('zahira/<int:pk>/ochirish/', views.reserve_delete, name='reserve_delete'),
    path('mebel/yangi/', views.furniture_create, name='furniture_create'),
    path('mebel/<int:pk>/tahrir/', views.furniture_edit, name='furniture_edit'),
    path('mebel/<int:pk>/ochirish/', views.furniture_delete, name='furniture_delete'),
    path('detallar/', views.detail_list, name='detail_list'),
    path('detallar/<int:pk>/tahrir/', views.detail_edit, name='detail_edit'),
    path('detallar/<int:pk>/ochirish/', views.detail_delete, name='detail_delete'),
    path('sotuv/yangi/', views.sale_create, name='sale_create'),
    path('sotuvlar/', views.sale_list, name='sale_list'),
    path('sotuv/<int:pk>/', views.sale_detail, name='sale_detail'),
    path('sotuv/<int:pk>/tolov/', views.add_payment, name='add_payment'),
    path('sotuv/<int:pk>/bekor/', views.sale_cancel, name='sale_cancel'),
    path('sotuv/<int:pk>/ochirish/', views.sale_delete, name='sale_delete'),
    path('sotuv/<int:pk>/nasiya-yopish/', views.close_credit, name='close_credit'),
    path('statistika/', views.statistics, name='statistics'),
    path('klientlar/', views.client_list, name='client_list'),
    path('klient/<int:pk>/', views.client_detail, name='client_detail'),
]
