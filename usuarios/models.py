from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver


# 1. Entidad PERSONAL
class Personal(models.Model):
    idPersonal = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=40)
    rut = models.CharField(max_length=12, unique=True)
    estado = models.CharField(max_length=20, default='Activo')

    def __str__(self):
        return f"{self.nombre} ({self.rut})"

    class Meta:
        db_table = 'PERSONAL'
        verbose_name = 'Personal'
        verbose_name_plural = 'Personal'


# 2. Entidad USUARIO (Relación 1 a 1 con PERSONAL)
class Usuario(AbstractUser):
    OPCIONES_CARGO = (
        ('Administrador', 'Administrador / Secretario'),
        ('Empleado', 'Trabajador de Campo'),
    )
    idUsuario = models.AutoField(primary_key=True)
    idPersonal = models.OneToOneField(
        Personal,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        db_column='idPersonal'
    )
    correo = models.EmailField(max_length=50, unique=True, null=True, blank=True)
    cargo = models.CharField(max_length=30, choices=OPCIONES_CARGO, default='Empleado')

    # Propiedades puente para compatibilidad con las vistas y plantillas
    @property
    def nombre(self):
        if self.idPersonal:
            return self.idPersonal.nombre
        return self.first_name or self.username

    @property
    def rut(self):
        if self.idPersonal:
            return self.idPersonal.rut
        return self.username

    def __str__(self):
        return f"{self.nombre} - {self.cargo}"

    class Meta:
        db_table = 'USUARIO'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'


# 3. Entidad ASISTENCIA
class Asistencia(models.Model):
    idAsistencia = models.AutoField(primary_key=True)
    idPersonal = models.ForeignKey(Personal, on_delete=models.CASCADE, db_column='idPersonal')
    fecha = models.DateField(auto_now_add=True)
    estadoAsistencia = models.CharField(max_length=20, default='No Registrado')

    def __str__(self):
        return f"Asistencia {self.fecha} - {self.idPersonal.nombre}"

    class Meta:
        db_table = 'ASISTENCIA'
        verbose_name = 'Asistencia'
        verbose_name_plural = 'Asistencias'


# 4. Entidad TAREA
class Tarea(models.Model):
    idTarea = models.AutoField(primary_key=True)
    nombreTarea = models.CharField(max_length=100)
    descripcion = models.TextField()
    fechaProgramada = models.DateField()
    horaInicio = models.CharField(max_length=5, default='08:00')
    horaFin = models.CharField(max_length=5, default='09:00')
    estadoAsignacion = models.CharField(max_length=20, default='Pendiente')

    def __str__(self):
        return f"{self.nombreTarea} ({self.fechaProgramada})"

    class Meta:
        db_table = 'TAREA'
        verbose_name = 'Tarea'
        verbose_name_plural = 'Tareas'


# 5. Entidad ASIGNACION_TAREA
class AsignacionTarea(models.Model):
    idAsignacion = models.AutoField(primary_key=True)
    idPersonal = models.ForeignKey(Personal, on_delete=models.CASCADE, db_column='idPersonal')
    idTarea = models.ForeignKey(Tarea, on_delete=models.CASCADE, db_column='idTarea')
    fechaAsignacion = models.DateField(auto_now_add=True)
    estadoAsignacion = models.CharField(max_length=20, default='Asignada')

    def __str__(self):
        return f"{self.idTarea.nombreTarea} -> {self.idPersonal.nombre}"

    class Meta:
        db_table = 'ASIGNACION_TAREA'
        verbose_name = 'Asignación de Tarea'
        verbose_name_plural = 'Asignaciones de Tareas'


# 6. Entidad CISTERNA
class Cisterna(models.Model):
    idCisterna = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, default="Estanque Principal")
    capacidad = models.IntegerField(default=50000)
    ubicacion = models.CharField(max_length=100, default="Fundo San Carlos")
    nivelMinimo = models.IntegerField(default=30)

    def __str__(self):
        return self.nombre

    class Meta:
        db_table = 'CISTERNA'
        verbose_name = 'Cisterna'
        verbose_name_plural = 'Cisternas'


# 7. Entidad LECTURA_SENSOR
class LecturaSensor(models.Model):
    idLectura = models.AutoField(primary_key=True)
    idCisterna = models.ForeignKey(Cisterna, on_delete=models.CASCADE, db_column='idCisterna')
    fechaHora = models.DateTimeField(auto_now_add=True)
    nivelAgua = models.IntegerField()
    porcentajeLlenado = models.IntegerField()

    def __str__(self):
        return f"Lectura {self.porcentajeLlenado}% - {self.fechaHora}"

    class Meta:
        db_table = 'LECTURA_SENSOR'
        verbose_name = 'Lectura de Sensor'
        verbose_name_plural = 'Lecturas de Sensores'


# 8. Entidad ALERTA
class Alerta(models.Model):
    idAlerta = models.AutoField(primary_key=True)
    idCisterna = models.ForeignKey(Cisterna, on_delete=models.CASCADE, db_column='idCisterna')
    fechaHora = models.DateTimeField(auto_now_add=True)
    descripcion = models.CharField(max_length=250)

    def __str__(self):
        return f"ALERTA: {self.descripcion}"

    class Meta:
        db_table = 'ALERTA'
        verbose_name = 'Alerta'
        verbose_name_plural = 'Alertas'


# Señal automática: garantiza que todo Usuario (incluso createsuperuser) tenga su registro en PERSONAL
@receiver(post_save, sender=Usuario)
def asegurar_personal_vinculado(sender, instance, created, **kwargs):
    if not instance.idPersonal:
        nombre_p = (instance.first_name + " " + instance.last_name).strip() or instance.username
        personal_obj, _ = Personal.objects.get_or_create(
            rut=instance.username[:12],
            defaults={'nombre': nombre_p[:40], 'estado': 'Activo'}
        )
        Usuario.objects.filter(pk=instance.pk).update(idPersonal=personal_obj)