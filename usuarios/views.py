import calendar
import json
from datetime import datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.urls import reverse
from .models import Usuario, Personal, Asistencia
from tareas.models import Tarea, AsignacionTarea, EstadoTareaDiaria
from cisterna.models import Cisterna, LecturaSensor, Alerta


def tiene_permisos_gestion(user):
    """Administrador y Secretario comparten acceso de gestión operativa."""
    return getattr(user, 'cargo', '') in ('Administrador', 'Secretario')


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


def parsear_meta_tarea(descripcion_raw):
    texto = (descripcion_raw or '').strip()
    prioridad = 'MEDIA'
    sector = 'General'
    if texto.startswith('[[') and ']]' in texto:
        cabecera, resto = texto[2:].split(']]', 1)
        partes = cabecera.split('|', 1)
        if len(partes) == 2:
            prioridad = partes[0].strip().upper() or 'MEDIA'
            sector = partes[1].strip() or 'General'
        texto = resto.strip()
    return prioridad, sector, texto


def construir_meta_tarea(prioridad, sector, descripcion_limpia):
    prio = (prioridad or 'MEDIA').strip().upper()
    sec = (sector or 'General').strip()
    desc = (descripcion_limpia or '').strip() or 'Asignación especial de campo.'
    return f"[[{prio}|{sec}]] {desc}"


def color_por_prioridad(prioridad):
    if prioridad == 'ALTA':
        return 'rose'
    if prioridad == 'MEDIA':
        return 'amber'
    return 'emerald'


def obtener_tareas_filtradas(user):
    qs = Tarea.objects.prefetch_related('asignaciontarea_set__idPersonal').order_by('-idTarea')
    if tiene_permisos_gestion(user):
        return qs
    if user.idPersonal:
        tareas_ids = AsignacionTarea.objects.filter(
            idPersonal=user.idPersonal
        ).values_list('idTarea', flat=True)
        return qs.filter(idTarea__in=tareas_ids)
    return Tarea.objects.none()


def construir_tareas_dia(user, fecha_obj):
    """Separa las tareas del día en (pendientes, en_proceso, completadas)."""
    fecha_iso = fecha_obj.strftime('%Y-%m-%d')

    estados_diarios = {
        e.tareaDiariaId: e
        for e in EstadoTareaDiaria.objects.filter(fecha=fecha_obj)
    }

    definicion_diarias = [
        {
            'id': 1,
            'titulo': 'Ordeña (Turno Mañana)',
            'horaInicio': '05:00',
            'horaFin': '07:00',
            'etiqueta': 'ALTA',
            'color': 'rose',
            'sector': 'Sala de Ordeña',
        },
        {
            'id': 2,
            'titulo': 'Limpieza Patios y Corrales',
            'horaInicio': '09:00',
            'horaFin': '12:00',
            'etiqueta': 'MEDIA',
            'color': 'amber',
            'sector': 'Corrales 1 al 4',
        },
        {
            'id': 3,
            'titulo': 'Ordeña (Turno Tarde)',
            'horaInicio': '14:00',
            'horaFin': '16:00',
            'etiqueta': 'ALTA',
            'color': 'rose',
            'sector': 'Sala de Ordeña',
        },
    ]

    pendientes = []
    en_proceso = []
    completadas = []

    for d in definicion_diarias:
        reg = estados_diarios.get(d['id'])
        esta_completada = reg.completada if reg else False

        item = {
            'id': d['id'],
            'es_puntual': False,
            'titulo': d['titulo'],
            'horaInicio': d['horaInicio'],
            'horaFin': d['horaFin'],
            'etiqueta': d['etiqueta'],
            'color': d['color'],
            'sector': d['sector'],
            'estado': 'Completada' if esta_completada else 'Pendiente',
            'encargados': user.nombre,
            'subtitulo': f"Sector: {d['sector']}",
            'detalle_url': f"{reverse('usuarios:detalle_tarea', args=[d['id']])}?fecha={fecha_iso}",
            'estado_url': reverse('usuarios:estado_tarea_diaria', args=[d['id']]),
        }

        if esta_completada:
            completadas.append(item)
        else:
            pendientes.append(item)

    for t in obtener_tareas_filtradas(user):
        f_ini = t.fechaProgramada
        esta_completada = (t.estadoAsignacion == 'Completada')

        if esta_completada:
            fecha_cierre = t.fechaCompletada or f_ini
            if fecha_obj != fecha_cierre:
                continue
            categoria = 'completada'
            estado_texto = 'Completada'
        else:
            if fecha_obj < f_ini:
                continue
            dias_transcurridos = (fecha_obj - f_ini).days + 1
            if t.estadoAsignacion == 'En Proceso' or dias_transcurridos > 1:
                categoria = 'en_proceso'
                estado_texto = f'En Proceso · Día {dias_transcurridos}' if dias_transcurridos > 1 else 'En Proceso'
            else:
                categoria = 'pendiente'
                estado_texto = 'Pendiente'

        prioridad, sector, desc_limpia = parsear_meta_tarea(t.descripcion)
        asignaciones = t.asignaciontarea_set.all()
        encargados = ", ".join(a.idPersonal.nombre for a in asignaciones) or "Sin asignar"
        ids_asignados = ",".join(str(a.idPersonal.idPersonal) for a in asignaciones)

        item = {
            'id': t.idTarea,
            'es_puntual': True,
            'titulo': t.nombreTarea,
            'prioridad': prioridad,
            'sector': sector,
            'descripcion_raw': desc_limpia,
            'ids_asignados': ids_asignados,
            'horaInicio': '99:99',
            'horaFin': '',
            'etiqueta': prioridad,
            'color': color_por_prioridad(prioridad),
            'estado': estado_texto,
            'encargados': encargados,
            'subtitulo': f"Sector: {sector} · {desc_limpia}",
            'detalle_url': f"{reverse('usuarios:detalle_tarea_puntual', args=[t.idTarea])}?fecha={fecha_iso}",
            'estado_url': reverse('usuarios:estado_tarea_puntual', args=[t.idTarea]),
            'editar_url': reverse('usuarios:editar_tarea_puntual', args=[t.idTarea]),
            'eliminar_url': reverse('usuarios:eliminar_tarea_puntual', args=[t.idTarea]),
        }

        if categoria == 'completada':
            completadas.append(item)
        elif categoria == 'en_proceso':
            en_proceso.append(item)
        else:
            pendientes.append(item)

    pendientes.sort(key=lambda x: (x['es_puntual'], x['horaInicio']))
    en_proceso.sort(key=lambda x: (x['es_puntual'], x['horaInicio']))
    completadas.sort(key=lambda x: (x['es_puntual'], x['horaInicio']))
    return pendientes, en_proceso, completadas


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

        nuevo_personal = Personal.objects.create(
            nombre=nombre_completo[:40],
            rut=rut[:12],
            estado='Activo'
        )

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


@login_required(login_url='/login/')
def inicio_view(request):
    hoy = datetime.now().date()

    dias_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    meses_es = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    fecha_hoy_texto = f"{dias_es[hoy.weekday()]}, {hoy.day} de {meses_es[hoy.month - 1]} {hoy.year}"

    pendientes_hoy, en_proceso_hoy, completadas_hoy = construir_tareas_dia(request.user, hoy)
    todas_tareas_hoy = pendientes_hoy + en_proceso_hoy + completadas_hoy

    total_tareas_hoy = len(todas_tareas_hoy)
    tareas_completadas_hoy = len(completadas_hoy)
    tareas_en_progreso_hoy = len(en_proceso_hoy)
    porcentaje_tareas_hoy = int((tareas_completadas_hoy / total_tareas_hoy) * 100) if total_tareas_hoy else 0

    personal_activo = Personal.objects.filter(estado='Activo').count()
    personal_total = Personal.objects.count()
    porcentaje_personal = int((personal_activo / personal_total) * 100) if personal_total else 100
    asistencias_hoy = Asistencia.objects.filter(fecha=hoy, estadoAsistencia='Presente').count()

    cisterna = Cisterna.objects.first()
    ultima_lectura = LecturaSensor.objects.order_by('-fechaHora').first()
    porcentaje_agua = ultima_lectura.porcentajeLlenado if ultima_lectura else 77
    litros_agua = ultima_lectura.nivelAgua if ultima_lectura else 38500
    capacidad_agua = cisterna.capacidad if cisterna else 50000
    nivel_minimo = cisterna.nivelMinimo if cisterna else 30

    alertas_recientes = Alerta.objects.order_by('-fechaHora')[:4]
    total_alertas = Alerta.objects.count()

    return render(request, 'inicio.html', {
        'fecha_hoy_texto': fecha_hoy_texto,
        'todas_tareas_hoy': todas_tareas_hoy,
        'total_tareas_hoy': total_tareas_hoy,
        'tareas_completadas_hoy': tareas_completadas_hoy,
        'tareas_en_progreso_hoy': tareas_en_progreso_hoy,
        'porcentaje_tareas_hoy': porcentaje_tareas_hoy,
        'personal_activo': personal_activo,
        'personal_total': personal_total,
        'porcentaje_personal': porcentaje_personal,
        'asistencias_hoy': asistencias_hoy,
        'cisterna': cisterna,
        'porcentaje_agua': porcentaje_agua,
        'litros_agua': litros_agua,
        'capacidad_agua': capacidad_agua,
        'nivel_minimo': nivel_minimo,
        'alertas_recientes': alertas_recientes,
        'total_alertas': total_alertas,
    })


@login_required(login_url='/login/')
def mis_tareas_view(request):
    hoy = datetime.now().date()
    fecha_param = request.GET.get('fecha', '')
    try:
        fecha_sel = datetime.strptime(fecha_param, '%Y-%m-%d').date() if fecha_param else hoy
    except ValueError:
        fecha_sel = hoy

    if request.method == 'POST' and tiene_permisos_gestion(request.user):
        nombre_tarea = request.POST.get('nombre_tarea', '').strip()
        prioridad = request.POST.get('prioridad', 'MEDIA')
        sector = request.POST.get('sector', 'General')
        descripcion_limpia = request.POST.get('descripcion', '').strip()
        fecha_str = request.POST.get('fecha_programada', '')
        personal_ids = request.POST.getlist('asignados_checkbox')

        try:
            fecha_prog = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            fecha_prog = fecha_sel

        if nombre_tarea:
            descripcion_guardada = construir_meta_tarea(prioridad, sector, descripcion_limpia)
            nueva_tarea = Tarea.objects.create(
                nombreTarea=nombre_tarea[:100],
                descripcion=descripcion_guardada,
                fechaProgramada=fecha_prog,
                fechaFin=None,
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

    dias_semana_largo = ["LU", "MA", "MI", "JU", "VI", "SA", "DO"]
    meses = ["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"]
    subtitulo_fecha = f"{dias_semana_largo[fecha_sel.weekday()]}, {fecha_sel.day} DE {meses[fecha_sel.month - 1]}, {fecha_sel.year}"

    pendientes, en_proceso, completadas = construir_tareas_dia(request.user, fecha_sel)
    personal = Personal.objects.filter(estado='Activo')

    return render(request, 'tareas.html', {
        'personal': personal,
        'pendientes': pendientes,
        'en_proceso': en_proceso,
        'completadas': completadas,
        'fecha_sel_iso': fecha_sel.strftime('%Y-%m-%d'),
        'subtitulo_fecha': subtitulo_fecha,
    })


@login_required(login_url='/login/')
def calendario_view(request):
    hoy = datetime.now().date()
    mes_param = request.GET.get('mes', '')

    try:
        if mes_param:
            anio, mes = map(int, mes_param.split('-'))
            primer_dia = datetime(anio, mes, 1).date()
        else:
            anio, mes = hoy.year, hoy.month
            primer_dia = datetime(anio, mes, 1).date()
    except (ValueError, TypeError):
        anio, mes = hoy.year, hoy.month
        primer_dia = datetime(anio, mes, 1).date()

    prev_fecha = (primer_dia - timedelta(days=1)).replace(day=1)
    ultimo_dia_mes = calendar.monthrange(anio, mes)[1]
    next_fecha = (datetime(anio, mes, ultimo_dia_mes).date() + timedelta(days=1)).replace(day=1)

    meses_es = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    dias_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    titulo_mes = f"{meses_es[mes - 1]} {anio}"

    cal = calendar.Calendar(firstweekday=0)
    semanas_raw = cal.monthdatescalendar(anio, mes)
    grid_inicio = semanas_raw[0][0]
    grid_fin = semanas_raw[-1][-1]

    # 1. Tareas diarias completadas en el rango visible
    diarias_regs = EstadoTareaDiaria.objects.filter(
        fecha__range=(grid_inicio, grid_fin),
        tareaDiariaId__in=[1, 2, 3],
        completada=True
    )
    diarias_por_fecha = {}
    for r in diarias_regs:
        diarias_por_fecha.setdefault(r.fecha, set()).add(r.tareaDiariaId)

    definicion_diarias = [
        {'id': 1, 'titulo': 'Ordeña (Turno Mañana)', 'horario': '05:00 - 07:00'},
        {'id': 2, 'titulo': 'Limpieza Patios y Corrales', 'horario': '09:00 - 12:00'},
        {'id': 3, 'titulo': 'Ordeña (Turno Tarde)', 'horario': '14:00 - 16:00'},
    ]

    # 2. Tareas puntuales
    tareas_puntuales = obtener_tareas_filtradas(request.user)
    eventos_por_fecha = {}

    for t in tareas_puntuales:
        f_ini = t.fechaProgramada
        prioridad, sector, _ = parsear_meta_tarea(t.descripcion)

        if t.estadoAsignacion == 'Completada':
            f_fin = t.fechaCompletada or f_ini
            if f_fin < f_ini:
                f_fin = f_ini
            color = 'green'
            span = (f_fin - f_ini).days + 1
            mostrar = True
        else:
            if f_ini > hoy:
                continue
            f_fin = hoy
            color = 'blue'
            span = (f_fin - f_ini).days + 1
            mostrar = (span >= 2) or (t.estadoAsignacion == 'En Proceso')

        if not mostrar or f_fin < grid_inicio or f_ini > grid_fin:
            continue

        iter_d = max(f_ini, grid_inicio)
        limite_d = min(f_fin, grid_fin)
        while iter_d <= limite_d:
            eventos_por_fecha.setdefault(iter_d, []).append({
                'f_ini': f_ini,
                'f_fin': f_fin,
                'color': color,
                'span': span,
                'titulo': t.nombreTarea,
                'sector': sector,
                'prioridad': prioridad,
                'estado': t.estadoAsignacion,
                'mismo_dia_completada': (t.estadoAsignacion == 'Completada' and span == 1),
                'cerrada_este_dia': (t.estadoAsignacion == 'Completada' and iter_d == f_fin),
            })
            iter_d += timedelta(days=1)

    semanas_calendario = []
    resumen_dias = {}

    for semana in semanas_raw:
        fila = []
        for d in semana:
            es_mes_actual = (d.month == mes)
            es_hoy = (d == hoy)
            fecha_iso = d.strftime('%Y-%m-%d')

            # Puntito de tareas diarias (medio)
            ids_comp = diarias_por_fecha.get(d, set())
            comp_diarias = len(ids_comp)
            if comp_diarias == 3:
                punto_diario = 'green'
            elif d <= hoy or comp_diarias > 0:
                punto_diario = 'yellow'
            else:
                punto_diario = 'none'

            lista_ev = eventos_por_fecha.get(d, [])

            # Indicador 1 (Arriba de las diarias): puntito verde si una tarea puntual se completó el mismo día
            tiene_puntual_mismo_dia = any(e['mismo_dia_completada'] for e in lista_ev)

            # Indicador 3 (Debajo de las diarias): óvalo largo (2+ días) o punto azul (1 día en proceso)
            eventos_inferiores = [e for e in lista_ev if not e['mismo_dia_completada']]
            indicador_inferior = None
            if eventos_inferiores:
                # Prioriza multi-día (span >= 2) para que el óvalo nunca se corte
                eventos_inferiores.sort(key=lambda x: (-x['span'], 0 if x['color'] == 'blue' else 1, x['f_ini']))
                ev = eventos_inferiores[0]
                es_multidia = (ev['span'] >= 2)
                es_inicio_tramo = (d == ev['f_ini']) or (d.weekday() == 0)
                es_fin_tramo = (d == ev['f_fin']) or (d.weekday() == 6)

                indicador_inferior = {
                    'color': ev['color'],
                    'es_multidia': es_multidia,
                    'es_inicio': es_inicio_tramo,
                    'es_fin': es_fin_tramo,
                }

            # Datos para el panel lateral derecho
            diarias_detalle = [
                {
                    'titulo': item['titulo'],
                    'horario': item['horario'],
                    'completada': (item['id'] in ids_comp),
                }
                for item in definicion_diarias
            ]

            en_proceso_detalle = [
                {
                    'titulo': e['titulo'],
                    'sector': e['sector'],
                    'dias': e['span'],
                }
                for e in lista_ev if e['estado'] != 'Completada'
            ]

            completadas_detalle = [
                {
                    'titulo': e['titulo'],
                    'sector': e['sector'],
                    'mismo_dia': e['mismo_dia_completada'],
                    'dias': e['span'],
                }
                for e in lista_ev if e['cerrada_este_dia']
            ]

            resumen_dias[fecha_iso] = {
                'fecha_texto': f"{dias_es[d.weekday()]} {d.day} de {meses_es[d.month - 1]}",
                'url_tareas': f"{reverse('usuarios:tareas')}?fecha={fecha_iso}",
                'diarias_todas_hechas': (comp_diarias == 3),
                'diarias_completadas': comp_diarias,
                'diarias_lista': diarias_detalle,
                'en_proceso_lista': en_proceso_detalle,
                'completadas_lista': completadas_detalle,
            }

            fila.append({
                'fecha_iso': fecha_iso,
                'dia': d.day,
                'es_mes_actual': es_mes_actual,
                'es_hoy': es_hoy,
                'tiene_puntual_mismo_dia': tiene_puntual_mismo_dia,
                'punto_diario': punto_diario,
                'indicador_inferior': indicador_inferior,
            })
        semanas_calendario.append(fila)

    return render(request, 'calendario.html', {
        'titulo_mes': titulo_mes,
        'prev_mes_iso': prev_fecha.strftime('%Y-%m'),
        'next_mes_iso': next_fecha.strftime('%Y-%m'),
        'hoy_iso': hoy.strftime('%Y-%m-%d'),
        'semanas_calendario': semanas_calendario,
        'resumen_dias_json': json.dumps(resumen_dias),
    })


@login_required(login_url='/login/')
def editar_tarea_puntual_view(request, tarea_id):
    if not tiene_permisos_gestion(request.user):
        return redirect('usuarios:tareas')

    tarea_obj = get_object_or_404(Tarea, idTarea=tarea_id)
    fecha_retorno = request.POST.get('fecha_retorno', tarea_obj.fechaProgramada.strftime('%Y-%m-%d'))

    if request.method == 'POST':
        nombre_tarea = request.POST.get('nombre_tarea', '').strip()
        prioridad = request.POST.get('prioridad', 'MEDIA')
        sector = request.POST.get('sector', 'General')
        descripcion_limpia = request.POST.get('descripcion', '').strip()
        personal_ids = request.POST.getlist('asignados_checkbox')

        if nombre_tarea:
            tarea_obj.nombreTarea = nombre_tarea[:100]
            tarea_obj.descripcion = construir_meta_tarea(prioridad, sector, descripcion_limpia)
            tarea_obj.save()

            AsignacionTarea.objects.filter(idTarea=tarea_obj).delete()
            trabajadores = Personal.objects.filter(idPersonal__in=personal_ids)
            for trabajador in trabajadores:
                AsignacionTarea.objects.create(
                    idPersonal=trabajador,
                    idTarea=tarea_obj,
                    estadoAsignacion='Asignada'
                )

            messages.success(request, 'Tarea puntual actualizada correctamente.')

    return redirect(f"{reverse('usuarios:tareas')}?fecha={fecha_retorno}")


@login_required(login_url='/login/')
def eliminar_tarea_puntual_view(request, tarea_id):
    if not tiene_permisos_gestion(request.user):
        return redirect('usuarios:tareas')

    tarea_obj = get_object_or_404(Tarea, idTarea=tarea_id)
    fecha_retorno = request.POST.get('fecha_retorno', datetime.now().strftime('%Y-%m-%d'))

    if request.method == 'POST':
        tarea_obj.delete()
        messages.success(request, 'Tarea puntual eliminada correctamente.')

    return redirect(f"{reverse('usuarios:tareas')}?fecha={fecha_retorno}")


@login_required(login_url='/login/')
def estado_tarea_puntual_view(request, tarea_id):
    tarea_obj = get_object_or_404(Tarea, idTarea=tarea_id)
    fecha_retorno = request.POST.get('fecha_retorno', datetime.now().strftime('%Y-%m-%d'))
    nuevo_estado = request.POST.get('nuevo_estado', 'Completada')

    try:
        fecha_obj = datetime.strptime(fecha_retorno, '%Y-%m-%d').date()
    except ValueError:
        fecha_obj = datetime.now().date()

    if request.method == 'POST':
        if tarea_obj.estadoAsignacion == 'Completada' and nuevo_estado == 'En Proceso':
            return redirect(f"{reverse('usuarios:tareas')}?fecha={fecha_retorno}")

        if nuevo_estado == 'Completada':
            tarea_obj.estadoAsignacion = 'Completada'
            tarea_obj.fechaCompletada = fecha_obj
        elif nuevo_estado == 'En Proceso':
            tarea_obj.estadoAsignacion = 'En Proceso'
            tarea_obj.fechaCompletada = None
        else:
            tarea_obj.estadoAsignacion = 'Pendiente'
            tarea_obj.fechaCompletada = None
        tarea_obj.save()

    return redirect(f"{reverse('usuarios:tareas')}?fecha={fecha_retorno}")


@login_required(login_url='/login/')
def estado_tarea_diaria_view(request, tarea_id):
    if tarea_id not in (1, 2, 3):
        return redirect('usuarios:tareas')

    fecha_retorno = request.POST.get('fecha_retorno', datetime.now().strftime('%Y-%m-%d'))
    nuevo_estado = request.POST.get('nuevo_estado', 'Completada')

    try:
        fecha_obj = datetime.strptime(fecha_retorno, '%Y-%m-%d').date()
    except ValueError:
        fecha_obj = datetime.now().date()

    if request.method == 'POST':
        reg, _ = EstadoTareaDiaria.objects.get_or_create(
            tareaDiariaId=tarea_id,
            fecha=fecha_obj
        )
        reg.completada = (nuevo_estado == 'Completada')
        reg.save()

    return redirect(f"{reverse('usuarios:tareas')}?fecha={fecha_obj.strftime('%Y-%m-%d')}")


@login_required(login_url='/login/')
def detalle_tarea_view(request, tarea_id):
    hoy = datetime.now().date()
    fecha_param = request.GET.get('fecha') or request.POST.get('fecha') or ''
    try:
        fecha_tarea = datetime.strptime(fecha_param, '%Y-%m-%d').date() if fecha_param else hoy
    except ValueError:
        fecha_tarea = hoy

    reg, _ = EstadoTareaDiaria.objects.get_or_create(
        tareaDiariaId=tarea_id,
        fecha=fecha_tarea
    )

    if request.method == 'POST':
        accion = request.POST.get('accion', 'finalizar')
        if accion == 'finalizar':
            reg.completada = True
            reg.save()
            messages.success(request, 'Tarea diaria confirmada como completada.')
        return redirect(f"{reverse('usuarios:tareas')}?fecha={fecha_tarea.strftime('%Y-%m-%d')}")

    tareas_diarias = {
        1: {
            'titulo': 'Ordeña (Turno Mañana)',
            'horario': '05:00 - 07:00',
            'prioridad': 'ALTA',
            'sector': 'Sala de Ordeña Principal',
            'descripcion': 'Proceso de ordeña matutina de todo el rebaño lechero. Incluye preparación de ubres, colocación de pezoneras, monitoreo de flujo y limpieza post-ordeño de los equipos.',
            'color': 'rose'
        },
        2: {
            'titulo': 'Limpieza Patios y Corrales',
            'horario': '09:00 - 12:00',
            'prioridad': 'MEDIA',
            'sector': 'Corrales 1 al 4',
            'descripcion': 'Remoción de estiércol mediante tractor rascador, lavado de patios de alimentación y corrales de espera. Revisión y limpieza de los bebederos automáticos.',
            'color': 'amber'
        },
        3: {
            'titulo': 'Ordeña (Turno Tarde)',
            'horario': '14:00 - 16:00',
            'prioridad': 'ALTA',
            'sector': 'Sala de Ordeña Principal',
            'descripcion': 'Segundo turno de ordeña del día. Mismo protocolo de higiene e inspección visual de las vacas que en el turno de la mañana.',
            'color': 'rose'
        }
    }

    info = tareas_diarias.get(tarea_id)
    if not info:
        return redirect('usuarios:tareas')

    tarea = {
        **info,
        'es_puntual': False,
        'tipo_tarea': 'Rutina Diaria Programada',
        'estado': 'Completada' if reg.completada else 'Pendiente',
        'fecha_inicio_texto': fecha_tarea.strftime('%d/%m/%Y'),
        'fecha_cierre_texto': fecha_tarea.strftime('%d/%m/%Y') if reg.completada else 'Pendiente en jornada',
        'duracion_texto': info['horario'],
        'equipo_detalle': [
            {
                'nombre': request.user.idPersonal.nombre if request.user.idPersonal else request.user.nombre,
                'rut': request.user.idPersonal.rut if request.user.idPersonal else request.user.username,
            }
        ],
        'fecha_iso': fecha_tarea.strftime('%Y-%m-%d'),
    }

    return render(request, 'detalle_tarea.html', {'tarea': tarea})


@login_required(login_url='/login/')
def detalle_tarea_puntual_view(request, tarea_id):
    tarea_obj = get_object_or_404(Tarea, idTarea=tarea_id)

    if not tiene_permisos_gestion(request.user):
        tiene_acceso = AsignacionTarea.objects.filter(
            idTarea=tarea_obj,
            idPersonal=request.user.idPersonal
        ).exists()
        if not tiene_acceso:
            return redirect('usuarios:tareas')

    fecha_param = request.GET.get('fecha') or request.POST.get('fecha') or tarea_obj.fechaProgramada.strftime('%Y-%m-%d')
    try:
        fecha_obj = datetime.strptime(fecha_param, '%Y-%m-%d').date()
    except ValueError:
        fecha_obj = datetime.now().date()

    if request.method == 'POST':
        accion = request.POST.get('accion', 'finalizar')
        if accion == 'finalizar':
            tarea_obj.estadoAsignacion = 'Completada'
            tarea_obj.fechaCompletada = fecha_obj
            tarea_obj.save()
            messages.success(request, 'Tarea puntual confirmada como completada.')
        elif accion == 'en_proceso':
            if tarea_obj.estadoAsignacion != 'Completada':
                tarea_obj.estadoAsignacion = 'En Proceso'
                tarea_obj.fechaCompletada = None
                tarea_obj.save()
                messages.info(request, 'Tarea marcada En Proceso.')
        return redirect(f"{reverse('usuarios:tareas')}?fecha={fecha_param}")

    prioridad, sector, desc_limpia = parsear_meta_tarea(tarea_obj.descripcion)
    asignaciones = AsignacionTarea.objects.filter(idTarea=tarea_obj).select_related('idPersonal')
    equipo_detalle = [
        {
            'nombre': a.idPersonal.nombre,
            'rut': a.idPersonal.rut,
        }
        for a in asignaciones
    ]

    if tarea_obj.estadoAsignacion == 'Completada' and tarea_obj.fechaCompletada:
        dias = max((tarea_obj.fechaCompletada - tarea_obj.fechaProgramada).days + 1, 1)
        fecha_cierre_texto = tarea_obj.fechaCompletada.strftime('%d/%m/%Y')
    else:
        dias = max((fecha_obj - tarea_obj.fechaProgramada).days + 1, 1)
        fecha_cierre_texto = 'Pendiente de cierre'

    duracion_texto = f"{dias} día" if dias == 1 else f"{dias} días"

    tarea_data = {
        'es_puntual': True,
        'tipo_tarea': 'Tarea Puntual de Campo',
        'titulo': tarea_obj.nombreTarea,
        'horario': f"Asignada desde el {tarea_obj.fechaProgramada.strftime('%d/%m/%Y')}",
        'prioridad': prioridad,
        'estado': tarea_obj.estadoAsignacion,
        'sector': sector,
        'descripcion': desc_limpia,
        'fecha_inicio_texto': tarea_obj.fechaProgramada.strftime('%d/%m/%Y'),
        'fecha_cierre_texto': fecha_cierre_texto,
        'duracion_texto': duracion_texto,
        'equipo_detalle': equipo_detalle,
        'fecha_iso': fecha_param,
        'color': color_por_prioridad(prioridad),
    }

    return render(request, 'detalle_tarea.html', {'tarea': tarea_data})


@login_required(login_url='/login/')
def gestion_usuarios_view(request):
    if not tiene_permisos_gestion(request.user):
        return redirect('usuarios:inicio')

    usuario_actual = Usuario.objects.select_related('idPersonal').filter(pk=request.user.pk).first()
    otros_usuarios = Usuario.objects.select_related('idPersonal').exclude(pk=request.user.pk).order_by('first_name', 'username')

    return render(request, 'gestion_usuarios.html', {
        'usuario_actual': usuario_actual,
        'otros_usuarios': otros_usuarios,
    })


@login_required(login_url='/login/')
def editar_usuario_view(request, usuario_id):
    if not tiene_permisos_gestion(request.user):
        return redirect('usuarios:inicio')

    usuario_obj = get_object_or_404(Usuario, pk=usuario_id)

    if usuario_obj.cargo == 'Administrador' and request.user.cargo != 'Administrador':
        messages.error(request, 'No tienes permisos para editar la cuenta del Administrador.')
        return redirect('usuarios:gestion_usuarios')

    if request.method == 'POST':
        accion = request.POST.get('accion', 'guardar_datos')

        if accion == 'guardar_datos':
            nuevo_correo = request.POST.get('correo', '').strip()
            if not nuevo_correo:
                messages.error(request, 'El correo electrónico no puede quedar vacío.')
                return redirect('usuarios:gestion_usuarios')

            correo_en_uso = Usuario.objects.filter(
                Q(correo__iexact=nuevo_correo) | Q(email__iexact=nuevo_correo)
            ).exclude(pk=usuario_obj.pk).exists()

            if correo_en_uso:
                messages.error(request, 'Ya existe otro usuario registrado con ese correo electrónico.')
                return redirect('usuarios:gestion_usuarios')

            usuario_obj.correo = nuevo_correo
            usuario_obj.email = nuevo_correo
            usuario_obj.save()
            messages.success(request, f'Correo de {usuario_obj.nombre or usuario_obj.username} actualizado correctamente.')

        elif accion == 'cambiar_rol':
            nuevo_rol = request.POST.get('nuevo_rol', '').strip()
            if usuario_obj.cargo == 'Administrador' or usuario_obj.pk == request.user.pk:
                messages.error(request, 'No es posible cambiar el rol de esta cuenta.')
            elif nuevo_rol in ('Secretario', 'Empleado'):
                usuario_obj.cargo = nuevo_rol
                usuario_obj.save()
                messages.success(request, f'Rol de {usuario_obj.nombre or usuario_obj.username} actualizado a {nuevo_rol}.')

    return redirect('usuarios:gestion_usuarios')


@login_required(login_url='/login/')
def configuracion_view(request):
    return render(request, 'configuracion.html')