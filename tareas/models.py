from django.db import models
from usuarios.models import Personal


# 4. Entidad TAREA
class Tarea(models.Model):
    idTarea = models.AutoField(primary_key=True)
    nombreTarea = models.CharField(max_length=100)
    descripcion = models.TextField()
    fechaProgramada = models.DateField()
    fechaFin = models.DateField(null=True, blank=True)
    horaInicio = models.CharField(max_length=5, default='08:00')
    horaFin = models.CharField(max_length=5, default='09:00')
    estadoAsignacion = models.CharField(max_length=20, default='Pendiente')
    fechaCompletada = models.DateField(null=True, blank=True)
    observaciones = models.TextField(blank=True, default='')

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


# Registro manual de confirmación y notas para las 3 tareas diarias fijas
class EstadoTareaDiaria(models.Model):
    idRegistro = models.AutoField(primary_key=True)
    tareaDiariaId = models.IntegerField()
    fecha = models.DateField()
    completada = models.BooleanField(default=False)
    observaciones = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'ESTADO_TAREA_DIARIA'
        unique_together = ('tareaDiariaId', 'fecha')