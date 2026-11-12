from django.urls import path

from . import views

app_name = "usuarios" 

urlpatterns = [
    path('', views.inicio_view, name="inicio"),
    path('login/', views.iniciar_usuarios, name="login"),
    path('register/', views.registro_usuarios, name="register"),
    path('tareas/', views.mis_tareas_view, name="tareas"),
    path('configuracion/', views.configuracion_view, name="configuracion"),
    path('logout/', views.cerrar_sesion, name="logout"),
]