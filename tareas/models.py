from django.db import models
from usuarios.models import Personal

# Create your models here.


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