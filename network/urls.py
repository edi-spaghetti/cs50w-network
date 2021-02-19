
from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login', views.login_view, name='login'),
    path('logout', views.logout_view, name='logout'),
    path('register', views.register, name='register'),

    # API Routes
    path('api/v1/search', views.search, name='search'),
    path('api/v1/update', views.update, name='update'),
    path('api/v1/create', views.create, name='create'),
]
