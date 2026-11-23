from django.urls import path
from sensores import views

urlpatterns = [
    path('lecturas/', views.api_lecturas),
]