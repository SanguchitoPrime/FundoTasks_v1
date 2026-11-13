from django.contrib import admin
from .models import Usuario, Personal, Asistencia, Tarea, AsignacionTarea, Cisterna

# Registramos los modelos para que se vean en la web
admin.site.register(Usuario)
admin.site.register(Personal)
admin.site.register(Asistencia)
admin.site.register(Tarea)
admin.site.register(AsignacionTarea)
admin.site.register(Cisterna)