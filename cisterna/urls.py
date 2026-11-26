from django.urls import path
from . import views

app_name = 'cisterna'

urlpatterns = [
    path('', views.panel_cisterna_view, name='panel'),
]