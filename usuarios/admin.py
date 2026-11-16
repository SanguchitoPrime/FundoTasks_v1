from django.contrib import admin
from .models import Usuario, Personal, Asistencia


# Registramos los modelos para que se vean en la web
admin.site.register(Usuario)
admin.site.register(Personal)
admin.site.register(Asistencia)