from django.db import models

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