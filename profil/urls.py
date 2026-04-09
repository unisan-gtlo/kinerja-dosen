from django.urls import path
from . import views

app_name = 'profil'

urlpatterns = [
    path('', views.index, name='index'),
]