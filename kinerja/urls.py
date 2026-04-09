from django.urls import path
from . import views

app_name = 'kinerja'

urlpatterns = [
    path('', views.index, name='index'),
]