from django.urls import path
from . import views

app_name = 'usuarios'

urlpatterns = [
    path('', views.inicio_view, name="inicio"),
    path('login/', views.iniciar_usuarios, name="login"),
    path('register/', views.registro_usuarios, name="register"),
    path('logout/', views.cerrar_sesion, name="logout"),
    path('tareas/', views.mis_tareas_view, name="tareas"),
    path('calendario/', views.calendario_view, name="calendario"),
    path('tareas/editar/<int:tarea_id>/', views.editar_tarea_puntual_view, name="editar_tarea_puntual"),
    path('tareas/eliminar/<int:tarea_id>/', views.eliminar_tarea_puntual_view, name="eliminar_tarea_puntual"),
    path('tareas/estado-puntual/<int:tarea_id>/', views.estado_tarea_puntual_view, name="estado_tarea_puntual"),
    path('tareas/estado-diaria/<int:tarea_id>/', views.estado_tarea_diaria_view, name="estado_tarea_diaria"),
    path('configuracion/', views.configuracion_view, name="configuracion"),
    path('gestion-usuarios/', views.gestion_usuarios_view, name="gestion_usuarios"),
    path('gestion-usuarios/editar/<int:usuario_id>/', views.editar_usuario_view, name="editar_usuario"),
    path('tarea/<int:tarea_id>/', views.detalle_tarea_view, name="detalle_tarea"),
    path('tarea/puntual/<int:tarea_id>/', views.detalle_tarea_puntual_view, name="detalle_tarea_puntual"),
]