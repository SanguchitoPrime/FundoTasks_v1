from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.urls import reverse
from .models import Usuario, Personal, Tarea, AsignacionTarea


# --- Funciones auxiliares de RUT ---
def normalizar_rut(rut_str):
    if not rut_str:
        return ""
    return rut_str.replace('.', '').replace(' ', '').strip().upper()


def validar_rut(rut):
    rut_limpio = normalizar_rut(rut).replace("-", "")
    if len(rut_limpio) < 8:
        return False

    cuerpo = rut_limpio[:-1]
    dv_ingresado = rut_limpio[-1]

    if not cuerpo.isdigit():
        return False

    reverso = map(int, reversed(cuerpo))
    factores = [2, 3, 4, 5, 6, 7] * 3
    suma = sum(d * f for d, f in zip(reverso, factores))
    mod = (-suma) % 11

    dv_calculado = 'K' if mod == 10 else str(mod)
    return dv_calculado == dv_ingresado


def obtener_tareas_filtradas(user):
    """Administradores ven todas las tareas; Empleados solo las asignadas a su idPersonal."""
    qs = Tarea.objects.prefetch_related('asignaciontarea_set__idPersonal').order_by('horaInicio')
    if user.cargo == 'Administrador':
        return qs
    if user.idPersonal:
        tareas_ids = AsignacionTarea.objects.filter(
            idPersonal=user.idPersonal
        ).values_list('idTarea', flat=True)
        return qs.filter(idTarea__in=tareas_ids)
    return Tarea.objects.none()


# --- Vistas de Autenticación ---
def registro_usuarios(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        apellido = request.POST.get('apellido', '').strip()
        nombre_completo = f"{nombre} {apellido}".strip()
        rut = normalizar_rut(request.POST.get('rut', ''))
        correo = request.POST.get('correo', '').strip()
        contrasena = request.POST.get('password')

        if not validar_rut(rut):
            messages.error(request, 'El RUT ingresado no es válido.')
            return render(request, 'register.html')

        if Personal.objects.filter(rut=rut).exists() or Usuario.objects.filter(username=rut).exists():
            messages.error(request, 'Ya existe una cuenta registrada con este RUT.')
            return render(request, 'register.html')

        if Usuario.objects.filter(Q(correo__iexact=correo) | Q(email__iexact=correo)).exists():
            messages.error(request, 'Ya existe una cuenta registrada con este correo.')
            return render(request, 'register.html')

        # 1. Crear registro en la tabla PERSONAL
        nuevo_personal = Personal.objects.create(
            nombre=nombre_completo[:40],
            rut=rut[:12],
            estado='Activo'
        )

        # 2. Crear registro en la tabla USUARIO vinculado 1 a 1 con idPersonal
        Usuario.objects.create_user(
            username=rut,
            email=correo,
            correo=correo,
            password=contrasena,
            first_name=nombre,
            last_name=apellido,
            cargo='Empleado',
            idPersonal=nuevo_personal
        )

        messages.success(request, 'Cuenta creada exitosamente. Ahora puedes iniciar sesión.')
        return redirect('usuarios:login')

    return render(request, 'register.html')


def iniciar_usuarios(request):
    if request.method == 'POST':
        identificador = request.POST.get('correo', '').strip()
        contrasena = request.POST.get('password')
        username_real = identificador

        if '@' in identificador:
            usuario_encontrado = Usuario.objects.filter(
                Q(correo__iexact=identificador) | Q(email__iexact=identificador)
            ).first()
            if usuario_encontrado:
                username_real = usuario_encontrado.username
        else:
            rut_limpio = normalizar_rut(identificador)
            usuario_encontrado = Usuario.objects.filter(
                Q(username__iexact=identificador) |
                Q(username__iexact=rut_limpio) |
                Q(idPersonal__rut__iexact=identificador) |
                Q(idPersonal__rut__iexact=rut_limpio)
            ).first()

            if not usuario_encontrado:
                for u in Usuario.objects.select_related('idPersonal').all():
                    rut_bd = normalizar_rut(u.idPersonal.rut) if u.idPersonal else normalizar_rut(u.username)
                    if rut_bd == rut_limpio:
                        usuario_encontrado = u
                        break

            if usuario_encontrado:
                username_real = usuario_encontrado.username

        user = authenticate(request, username=username_real, password=contrasena)

        if user is not None:
            login(request, user)
            return redirect('usuarios:inicio')
        else:
            messages.error(request, 'RUT/Correo o contraseña incorrectos.')

    return render(request, 'login.html')


def cerrar_sesion(request):
    logout(request)
    return redirect('usuarios:login')


# --- Vistas Principales del Sistema ---
@login_required(login_url='/login/')
def inicio_view(request):
    hoy = datetime.now().date()
    tareas_puntuales_hoy = obtener_tareas_filtradas(request.user).filter(fechaProgramada=hoy)

    for t in tareas_puntuales_hoy:
        asignaciones = t.asignaciontarea_set.all()
        t.lista_encargados = ", ".join(a.idPersonal.nombre for a in asignaciones) or "Sin asignar"

    return render(request, 'inicio.html', {
        'tareas_puntuales_hoy': tareas_puntuales_hoy
    })


@login_required(login_url='/login/')
def mis_tareas_view(request):
    if request.method == 'POST' and request.user.cargo == 'Administrador':
        nombre_tarea = request.POST.get('nombre_tarea', '').strip()
        hora_inicio = request.POST.get('hora_inicio', '08:00')
        hora_fin = request.POST.get('hora_fin', '09:00')
        descripcion = request.POST.get('descripcion', '').strip() or 'Asignación Especial'
        fecha_str = request.POST.get('fecha_programada', '')
        personal_ids = request.POST.getlist('asignados_checkbox')

        try:
            fecha_prog = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            fecha_prog = datetime.now().date()

        if nombre_tarea:
            nueva_tarea = Tarea.objects.create(
                nombreTarea=nombre_tarea[:100],
                descripcion=descripcion,
                fechaProgramada=fecha_prog,
                horaInicio=hora_inicio,
                horaFin=hora_fin,
                estadoAsignacion='Pendiente'
            )

            trabajadores = Personal.objects.filter(idPersonal__in=personal_ids)
            for trabajador in trabajadores:
                AsignacionTarea.objects.create(
                    idPersonal=trabajador,
                    idTarea=nueva_tarea,
                    estadoAsignacion='Asignada'
                )

            messages.success(request, 'Tarea puntual creada y asignada correctamente.')
            return redirect(f"{reverse('usuarios:tareas')}?fecha={fecha_prog.strftime('%Y-%m-%d')}")

    personal = Personal.objects.filter(estado='Activo')
    tareas_puntuales = obtener_tareas_filtradas(request.user)

    for t in tareas_puntuales:
        asignaciones = t.asignaciontarea_set.all()
        t.lista_encargados = ", ".join(a.idPersonal.nombre for a in asignaciones) or "Sin asignar"

    return render(request, 'tareas.html', {
        'personal': personal,
        'tareas_puntuales': tareas_puntuales,
    })


@login_required(login_url='/login/')
def detalle_tarea_view(request, tarea_id):
    now = datetime.now()
    hoy = now.date()
    current_time = now.strftime("%H:%M")

    fecha_param = request.GET.get('fecha', '')
    try:
        fecha_tarea = datetime.strptime(fecha_param, '%Y-%m-%d').date() if fecha_param else hoy
    except ValueError:
        fecha_tarea = hoy

    def get_status(start, end):
        if fecha_tarea < hoy:
            return 'Completada'
        elif fecha_tarea > hoy:
            return 'Pendiente'
        if current_time > end:
            return 'Completada'
        elif start <= current_time <= end:
            return 'En Progreso'
        return 'Pendiente'

    tareas_diarias = {
        1: {
            'titulo': 'Ordeña (Turno Mañana)',
            'horario': '05:00 - 07:00',
            'prioridad': 'ALTA',
            'estado': get_status('05:00', '07:00'),
            'sector': 'Sala de Ordeña Principal',
            'descripcion': 'Proceso de ordeña matutina de todo el rebaño lechero. Incluye preparación de ubres, colocación de pezoneras, monitoreo de flujo y limpieza post-ordeño de los equipos.',
            'encargados': request.user.nombre,
            'color': 'rose'
        },
        2: {
            'titulo': 'Limpieza Patios y Corrales',
            'horario': '09:00 - 12:00',
            'prioridad': 'MEDIA',
            'estado': get_status('09:00', '12:00'),
            'sector': 'Corrales 1 al 4',
            'descripcion': 'Remoción de estiércol mediante tractor rascador, lavado de patios de alimentación y corrales de espera. Revisión y limpieza de los bebederos automáticos.',
            'encargados': request.user.nombre,
            'color': 'amber'
        },
        3: {
            'titulo': 'Ordeña (Turno Tarde)',
            'horario': '14:00 - 16:00',
            'prioridad': 'ALTA',
            'estado': get_status('14:00', '16:00'),
            'sector': 'Sala de Ordeña Principal',
            'descripcion': 'Segundo turno de ordeña del día. Mismo protocolo de higiene e inspección visual de las vacas que en el turno de la mañana.',
            'encargados': request.user.nombre,
            'color': 'rose'
        }
    }

    tarea = tareas_diarias.get(tarea_id)
    if not tarea:
        return redirect('usuarios:tareas')

    return render(request, 'detalle_tarea.html', {'tarea': tarea})


@login_required(login_url='/login/')
def detalle_tarea_puntual_view(request, tarea_id):
    tarea_obj = get_object_or_404(Tarea, idTarea=tarea_id)

    if request.user.cargo != 'Administrador':
        tiene_acceso = AsignacionTarea.objects.filter(
            idTarea=tarea_obj,
            idPersonal=request.user.idPersonal
        ).exists()
        if not tiene_acceso:
            return redirect('usuarios:tareas')

    now = datetime.now()
    hoy = now.date()
    hora_actual = now.strftime("%H:%M")

    if tarea_obj.fechaProgramada < hoy:
        estado = 'Completada'
    elif tarea_obj.fechaProgramada > hoy:
        estado = 'Pendiente'
    else:
        if hora_actual > tarea_obj.horaFin:
            estado = 'Completada'
        elif tarea_obj.horaInicio <= hora_actual <= tarea_obj.horaFin:
            estado = 'En Progreso'
        else:
            estado = 'Pendiente'

    asignaciones = AsignacionTarea.objects.filter(idTarea=tarea_obj).select_related('idPersonal')
    encargados = ", ".join(a.idPersonal.nombre for a in asignaciones) or "Sin asignar"

    tarea_data = {
        'titulo': tarea_obj.nombreTarea,
        'horario': f"{tarea_obj.horaInicio} - {tarea_obj.horaFin}",
        'prioridad': 'PUNTUAL',
        'estado': estado,
        'sector': 'Asignación Especial',
        'descripcion': tarea_obj.descripcion,
        'encargados': encargados,
        'color': 'indigo'
    }

    return render(request, 'detalle_tarea.html', {'tarea': tarea_data})


@login_required(login_url='/login/')
def configuracion_view(request):
    return render(request, 'configuracion.html')