from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Cisterna, LecturaSensor, Alerta


@login_required(login_url='/login/')
def panel_cisterna_view(request):
    cisterna = Cisterna.objects.first()
    lecturas = LecturaSensor.objects.order_by('-fechaHora')[:10]
    alertas = Alerta.objects.order_by('-fechaHora')[:10]
    return render(request, 'panel.html', {
        'cisterna': cisterna,
        'lecturas': lecturas,
        'alertas': alertas,
    })