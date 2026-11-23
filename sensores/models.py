from django.db import models

class LecturaSensor(models.Model):
    distancia = models.FloatField()
    nivel_cm = models.FloatField()
    porcentaje = models.FloatField()
    litros = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "lecturas_sensor"