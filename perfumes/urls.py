from django.urls import path
from . import views
urlpatterns = [
    path('', views.home_view, name='home'),
    path('products/', views.store_view, name='store_view'),
    path('add/', views.add_perfume_view, name='add_perfume'),
    path('api/buy/', views.purchase_perfume_api, name='purchase_perfume_api'),
    path('api/stock/', views.PerfumeStockView.as_view(), name='perfume_stock_api'),
    path('register/', views.register_view, name='register'),
    path('login/', views.LoginWithMessageView.as_view(), name='login'),
    path('logout/', views.LogoutWithMessageView.as_view(), name='logout'),
]
