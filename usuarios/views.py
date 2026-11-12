from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .models import Usuario  # <-- Importante para poder crear usuarios

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
        nombre = request.POST.get('nombre')
        rut = request.POST.get('rut')
        correo = request.POST.get('correo')
        contrasena = request.POST.get('password')
        
        # Validar el RUT
        if not validar_rut(rut):
            messages.error(request, 'El RUT ingresado no es válido.')
            return render(request, 'register.html')
            
        # Verificar si ya existe el RUT
        if Usuario.objects.filter(rut=rut).exists() or Usuario.objects.filter(username=rut).exists():
            messages.error(request, 'Ya existe una cuenta con este RUT.')
            return render(request, 'register.html')
            
        # Crear usuario (usamos el RUT como username interno)
        user = Usuario.objects.create_user(
            username=rut,
            email=correo,
            password=contrasena,
            rut=rut,
            nombre=nombre,
            first_name=nombre,
            cargo='Empleado'
        )
        
        messages.success(request, 'Cuenta creada exitosamente. Ahora puedes iniciar sesión.')
        return redirect('usuarios:login')

    return render(request, 'register.html')

# 3. Vista con la lógica de inicio de sesión
def iniciar_usuarios(request):
    if request.method == 'POST':
        correo = request.POST.get('correo')
        contrasena = request.POST.get('password')
        
        # Verifica si el usuario y la contraseña coinciden en la BD
        user = authenticate(request, username=correo, password=contrasena)
        
        if user is not None:
            login(request, user)
            # Redirige a inicio_view una vez que el login es exitoso
            return redirect('usuarios:inicio') 
        else:
            messages.error(request, 'Correo o contraseña incorrectos.')
            
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