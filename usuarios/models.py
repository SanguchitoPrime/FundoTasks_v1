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