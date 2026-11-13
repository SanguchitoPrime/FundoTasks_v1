from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .models import Usuario, Personal, Asistencia, Tarea, AsignacionTarea, Cisterna
from datetime import datetime

@login_required(login_url='/login/')
def mis_tareas_view(request):
    # 1. Buscamos TODOS los usuarios en la base de datos
    usuarios = Usuario.objects.all()
    
    # 2. Se los enviamos al HTML empaquetados en el diccionario
    return render(request, 'tareas.html', {'usuarios': usuarios})

@login_required(login_url='/login/')
def detalle_tarea_view(request, tarea_id):
    # Obtenemos la hora actual del sistema
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    
    # Función interna para calcular el estado
    def get_status(start, end):
        if current_time > end: return 'Completada'
        elif start <= current_time <= end: return 'En Progreso'
        return 'Pendiente'

    tareas_diarias = {
        1: {
            'titulo': 'Ordeña (Turno Mañana)',
            'horario': '05:00 - 07:00',
            'prioridad': 'ALTA',
            'estado': get_status('05:00', '07:00'),
            'sector': 'Sala de Ordeña Principal',
            'descripcion': 'Proceso de ordeña matutina de todo el rebaño lechero. Incluye preparación de ubres, colocación de pezoneras, monitoreo de flujo y limpieza post-ordeño de los equipos.',
            'color': 'rose'
        },
        2: {
            'titulo': 'Limpieza Patios y Corrales',
            'horario': '09:00 - 12:00',
            'prioridad': 'MEDIA',
            'estado': get_status('09:00', '12:00'),
            'sector': 'Corrales 1 al 4',
            'descripcion': 'Remoción de estiércol mediante tractor rascador, lavado de patios de alimentación y corrales de espera. Revisión y limpieza de los bebederos automáticos.',
            'color': 'amber'
        },
        3: {
            'titulo': 'Ordeña (Turno Tarde)',
            'horario': '14:00 - 16:00',
            'prioridad': 'ALTA',
            'estado': get_status('14:00', '16:00'),
            'sector': 'Sala de Ordeña Principal',
            'descripcion': 'Segundo turno de ordeña del día. Mismo protocolo de higiene e inspección visual de las vacas que en el turno de la mañana.',
            'color': 'rose'
        }
    }
    
    tarea = tareas_diarias.get(tarea_id)
    if not tarea:
        return redirect('usuarios:tareas')
        
    return render(request, 'detalle_tarea.html', {'tarea': tarea})

# --- Función para validar RUT chileno ---
def validar_rut(rut):
    # Limpiamos puntos y guiones
    rut_limpio = rut.upper().replace("-", "").replace(".", "")
    if len(rut_limpio) < 8:
        return False
    
    cuerpo = rut_limpio[:-1]
    dv_ingresado = rut_limpio[-1]

    if not cuerpo.isdigit():
        return False

    # Algoritmo Módulo 11
    reverso = map(int, reversed(cuerpo))
    factores = [2, 3, 4, 5, 6, 7] * 3  # Suficientes para cualquier RUT
    suma = sum(d * f for d, f in zip(reverso, factores))
    mod = (-suma) % 11

    dv_calculado = 'K' if mod == 10 else str(mod)
    return dv_calculado == dv_ingresado

# 1. Esta es la vista que faltaba y causaba el error
@login_required(login_url='/login/')
def inicio_view(request):
    return render(request, 'inicio.html')

# 2. Vista para registrar usuarios
def registro_usuarios(request):
    if request.method == 'POST':
        # Recibimos el nombre y apellido por separado
        nombre = request.POST.get('nombre')
        apellido = request.POST.get('apellido')
        
        # Los unimos en una sola variable con un espacio en medio
        nombre_completo = f"{nombre} {apellido}"
        
        rut = request.POST.get('rut')
        correo = request.POST.get('correo')
        contrasena = request.POST.get('password')
        
        user = Usuario.objects.create_user(
            username=rut,
            email=correo,
            password=contrasena,
            rut=rut,
            nombre=nombre_completo, # Nuestro campo personalizado
            first_name=nombre,      # Campo interno de Django
            last_name=apellido,     # Campo interno de Django
            cargo='Empleado'
        )
        
        messages.success(request, 'Cuenta creada exitosamente. Ahora puedes iniciar sesión.')
        return redirect('usuarios:login')

    return render(request, 'register.html')

# 3. Vista con la lógica de inicio de sesión
# Vista con la Lógica de inicio de sesión
def iniciar_usuarios(request):
    if request.method == 'POST':
        identificador = request.POST.get('correo') # Este campo recibe RUT o Correo
        contrasena = request.POST.get('password')
        
        # Por defecto, asumimos que el usuario escribió su RUT
        username_real = identificador 
        
        # Si lo que escribió tiene un '@', sabemos que es un correo
        if '@' in identificador:
            # Buscamos en la base de datos al usuario que tenga ese correo
            usuario_encontrado = Usuario.objects.filter(email=identificador).first()
            if usuario_encontrado:
                # Si lo encuentra, sacamos su RUT interno para poder loguearlo
                username_real = usuario_encontrado.username

        # Ahora sí, verificamos con Django usando el username_real (que siempre será el RUT)
        user = authenticate(request, username=username_real, password=contrasena)

        if user is not None:
            login(request, user)
            return redirect('usuarios:inicio')
        else:
            messages.error(request, 'RUT/Correo o contraseña incorrectos.')

    return render(request, 'login.html')

@login_required(login_url='/login/')
def mis_tareas_view(request):
    return render(request, 'tareas.html')

@login_required(login_url='/login/')
def configuracion_view(request):
    return render(request, 'configuracion.html')

def cerrar_sesion(request):
    logout(request)
    return redirect('usuarios:login')