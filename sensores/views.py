import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import LecturaSensor

@csrf_exempt
@require_POST
def api_lecturas(request):
    try:
        d = json.loads(request.body)
        lectura = LecturaSensor.objects.using("supabase").create(
            distancia=d["distancia"],
            nivel_cm=d["nivel_cm"],
            porcentaje=d["porcentaje"],
            litros=d["litros"],
        )
    except (KeyError, ValueError):
        return JsonResponse({"error": "datos inválidos"}, status=400)
    return JsonResponse({"id": lectura.id}, status=201)