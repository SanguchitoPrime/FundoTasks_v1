from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Usuario)
def sincronizar_personal(sender, instance, created, **kwargs):
    if created:
        # Si el usuario es nuevo, creamos su registro en Personal
        Personal.objects.create(
            rut=instance.rut or instance.username,
            nombre=instance.nombre or instance.username,
            cargo=instance.cargo,
            estado='Activo'
        )
    else:
        # Si el usuario se actualizó (ej. le cambiaste el cargo a Admin), actualizamos Personal
        personal = Personal.objects.filter(rut=instance.rut or instance.username).first()
        if personal:
            personal.nombre = instance.nombre or instance.username
            personal.cargo = instance.cargo
            personal.save()
# 1. Modelo de Usuario (Autenticación y Roles)
class Usuario(AbstractUser):
    OPCIONES_CARGO = (
        ('Administrador', 'Administrador / Secretario'),
        ('Empleado', 'Trabajador de Campo'),
    )
    cargo = models.CharField(max_length=30, choices=OPCIONES_CARGO, default='Empleado')
    rut = models.CharField(max_length=12, unique=True, null=True, blank=True)
    nombre = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return f"{self.nombre or self.username} - {self.cargo}"


# 2. Modelo de Personal (Trabajadores del predio)
# 2. Modelo de Personal (Trabajadores del predio)
class Personal(models.Model):
    idPersonal = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=40)
    rut = models.CharField(max_length=12, unique=True)
    cargo = models.CharField(max_length=20)
    estado = models.CharField(max_length=20, default='Activo')

    def __str__(self):
        return f"{self.nombre} ({self.rut})"
        
    # Añade esto para arreglar el nombre en el panel de admin
    class Meta:
        verbose_name = "Personal"
        verbose_name_plural = "Personal"


# 3. Modelo de Asistencia diaria del personal
class Asistencia(models.Model):
    idAsistencia = models.AutoField(primary_key=True)
    idPersonal = models.ForeignKey(Personal, on_delete=models.CASCADE)
    fecha = models.DateField(auto_now_add=True)
    estadoAsistencia = models.CharField(max_length=20, default='No Registrado') # Registrado / No Registrado
    observacion = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Asistencia {self.fecha} - {self.idPersonal.nombre}"


# 4. Modelo de Tareas generales del fundo
class Tarea(models.Model):
    idTarea = models.AutoField(primary_key=True)
    nombre_tarea = models.CharField(max_length=100)
    descripcion = models.TextField()
    fecha_programada = models.DateField()
    estado_tarea = models.CharField(max_length=20, default='Pendiente') # Pendiente, En Proceso, Completada, Cancelada

    def __str__(self):
        return self.nombre_tarea


# 5. Modelo de Asignación de Tareas a los trabajadores
class AsignacionTarea(models.Model):
    idAsignacion = models.AutoField(primary_key=True)
    idPersonal = models.ForeignKey(Personal, on_delete=models.CASCADE)
    idTarea = models.ForeignKey(Tarea, on_delete=models.CASCADE)
    fecha_asignacion = models.DateField(auto_now_add=True)
    estado_asignacion = models.CharField(max_length=20, default='Asignada')

    def __str__(self):
        return f"Tarea {self.idTarea.nombre_tarea} -> {self.idPersonal.nombre}"


# 6. Modelo de Cisterna (Recursos Hídricos)
class Cisterna(models.Model):
    idCisterna = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, default="Estanque Principal")
    capacidad = models.IntegerField(default=30000) # En litros
    ubicacion = models.CharField(max_length=100)
    nivelMinimo = models.IntegerField(default=30) # Porcentaje de alerta baja

    def __str__(self):
        return self.nombre


# 7. Modelo de Lectura del Sensor (IoT - JSN-SR04T)
class LecturaSensor(models.Model):
    idLectura = models.AutoField(primary_key=True)
    idCisterna = models.ForeignKey(Cisterna, on_delete=models.CASCADE)
    fechaHora = models.DateTimeField(auto_now_add=True)
    nivelAgua = models.IntegerField() # En centímetros
    porcentajeLlenado = models.IntegerField() # Calculado del 0 al 100%

    def __str__(self):
        return f"Lectura {self.porcentajeLlenado}% - {self.fechaHora}"


# 8. Modelo de Alertas generadas por niveles críticos
class Alerta(models.Model):
    idAlerta = models.AutoField(primary_key=True)
    idCisterna = models.ForeignKey(Cisterna, on_delete=models.CASCADE)
    fechaHora = models.DateTimeField(auto_now_add=True)
    descripcion = models.CharField(max_length=250)

    def __str__(self):
        return f"ALERTA: {self.descripcion}"