from django.shortcuts import render
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
import json

from .models import Nivel, Carta, Partida, Estadistica
from .services.game_engine import (
    create_game,
    reveal_card,
    hide_unmatched,
    serialize_game_state,
)



# -----------------------------
# 🎮 TABLERO PRINCIPAL (JUEGO)
# -----------------------------
@login_required
def game_board(request):
    nivel_nombre = request.GET.get("nivel", "fácil").capitalize()

    # ✅ Buscar el nivel actual
    nivel = Nivel.objects.filter(nombre__iexact=nivel_nombre).first()
    if not nivel:
        nivel = Nivel.objects.first()

    # ✅ Buscar partida activa o crear una nueva
    partida = Partida.objects.filter(usuario=request.user, activa=True, nivel=nivel).first()
    if not partida:
        partida = create_game(request.user, nivel)

    # ✅ Obtener cartas de la partida
    cartas = Carta.objects.filter(partida=partida).order_by("posicion")

    # ✅ Asegurar que existan los contadores en la sesión
    if 'movimientos' not in request.session:
        request.session['movimientos'] = 0
    if 'aciertos' not in request.session:
        request.session['aciertos'] = 0

    # ✅ Pasar datos al template
    return render(request, "Juegos.html", {
        "nivel": nivel,
        "cartas": cartas,
        "movimientos": request.session['movimientos'],
        "aciertos": request.session['aciertos'],
    })









# -----------------------------
# 🆕 CREAR NUEVA PARTIDA
# -----------------------------
@csrf_exempt
def new_game(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    data = json.loads(request.body.decode('utf-8'))
    username = data.get('usuario')
    nivel_id = data.get('nivel_id')

    if not username or not nivel_id:
        return JsonResponse({'error': 'usuario y nivel_id son requeridos'}, status=400)

    user = get_object_or_404(User, username=username)
    nivel = get_object_or_404(Nivel, id=nivel_id)
    partida = create_game(user, nivel)

    return JsonResponse({
        'mensaje': 'Partida creada correctamente',
        'partida_id': partida.id,
        'estado': serialize_game_state(partida)
    })




# -----------------------------
# 🃏 REVELAR CARTA (FINAL COMPLETA)
# -----------------------------

from django.utils import timezone
from .models import Carta, Partida, Nivel
from .services.game_engine import actualizar_estadisticas

def reveal_card(request, pos):
    """Revela una carta, registra movimientos, guarda estadísticas y avanza de nivel."""
    cartas_ids = request.session.get('cartas', [])
    revealed = request.session.get('revealed', [])
    matched = request.session.get('matched', [])
    movimientos = request.session.get('movimientos', 0)
    aciertos = request.session.get('aciertos', 0)

    if pos >= len(cartas_ids):
        return JsonResponse({'error': 'Posición inválida'})

    carta_id = cartas_ids[pos]

    if carta_id in matched:
        estado = generar_estado(cartas_ids, revealed, matched, movimientos, aciertos)
        return JsonResponse({'estado_partida': estado})

    if carta_id not in revealed:
        revealed.append(carta_id)

    # Si hay dos cartas reveladas, verificamos
    if len(revealed) == 2:
        movimientos += 1
        carta1 = Carta.objects.get(id=revealed[0])
        carta2 = Carta.objects.get(id=revealed[1])

        if carta1.valor == carta2.valor:
            matched.extend(revealed)
            aciertos += 1

        revealed = []

        partida = Partida.objects.filter(usuario=request.user, activa=True).last()
        if partida:
            partida.movimientos = movimientos
            partida.aciertos = aciertos

            total_cartas = len(cartas_ids)
            total_pares = total_cartas // 2

            # ✅ Si ganó el nivel
            if aciertos >= total_pares:
                partida.ganada = True
                partida.activa = False
                partida.fecha_fin = timezone.now()
                partida.save()

                # Actualiza estadísticas
                actualizar_estadisticas(partida)

                # Calcula siguiente nivel
                niveles = list(Nivel.objects.all().order_by('dificultad'))
                actual_index = next((i for i, n in enumerate(niveles) if n.id == partida.nivel.id), -1)
                siguiente = niveles[actual_index + 1] if (actual_index + 1 < len(niveles)) else niveles[0]

                return JsonResponse({
                    'estado_partida': generar_estado(cartas_ids, revealed, matched, movimientos, aciertos, True),
                    'mensaje': f'🎉 ¡Has ganado el nivel {partida.nivel.nombre}! Pasando a {siguiente.nombre}...',
                    'siguiente_nivel': siguiente.nombre
                })
            else:
                partida.save()

    ganada = len(matched) == len(cartas_ids)

    request.session['revealed'] = revealed
    request.session['matched'] = matched
    request.session['movimientos'] = movimientos
    request.session['aciertos'] = aciertos

    estado = generar_estado(cartas_ids, revealed, matched, movimientos, aciertos, ganada)
    return JsonResponse({'estado_partida': estado})











# -----------------------------
# 🔁 GENERAR ESTADO DEL JUEGO (ACTUALIZADO)
# -----------------------------
def generar_estado(cartas_ids, revealed, matched, movimientos=0, aciertos=0, ganada=False):
    cartas = []
    for cid in cartas_ids:
        carta = Carta.objects.get(id=cid)
        cartas.append({
            'simbolo': carta.simbolo if cid in revealed or cid in matched else '',
            'revelada': cid in revealed,
            'emparejada': cid in matched,
        })
    return {
        'cartas': cartas,
        'movimientos': movimientos,
        'aciertos': aciertos,
        'ganada': ganada,
    }







def generar_estado(cartas_ids, revealed, matched, movimientos=0, aciertos=0, ganada=False):
    cartas = []
    for cid in cartas_ids:
        carta = Carta.objects.get(id=cid)
        cartas.append({
            'simbolo': carta.simbolo if cid in revealed or cid in matched else '',
            'revelada': cid in revealed,
            'emparejada': cid in matched
        })
    return {
        'cartas': cartas,
        'movimientos': movimientos,
        'aciertos': aciertos,
        'ganada': ganada
    }














# -----------------------------
# 🔄 OCULTAR CARTAS INCORRECTAS
# -----------------------------
@csrf_exempt
def hide(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    data = json.loads(request.body.decode('utf-8'))
    partida_id = data.get('partida_id')
    pos1 = data.get('pos1')
    pos2 = data.get('pos2')

    if not all([partida_id, pos1, pos2]):
        return JsonResponse({'error': 'partida_id, pos1 y pos2 son requeridos'}, status=400)

    partida = get_object_or_404(Partida, id=partida_id)
    resultado = hide_unmatched(partida, pos1, pos2)
    return JsonResponse(resultado)


# -----------------------------
# 📊 ESTADO DE LA PARTIDA
# -----------------------------
def game_state(request, partida_id):
    partida = get_object_or_404(Partida, id=partida_id)
    return JsonResponse(serialize_game_state(partida))


# -----------------------------
# 📈 CAMBIAR DE NIVEL
# -----------------------------
@login_required
def cambiar_nivel(request):
    niveles = list(Nivel.objects.all().order_by("dificultad"))
    actual_nombre = request.GET.get("nivel", "fácil").lower()

    # Buscar el siguiente nivel
    for i, n in enumerate(niveles):
        if n.nombre.lower() == actual_nombre:
            siguiente = niveles[i + 1] if i + 1 < len(niveles) else niveles[0]
            return render(request, "Juegos.html", {
                "nivel": siguiente,
                "cartas": Carta.objects.filter(nivel=siguiente).order_by("posicion")
            })

    return render(request, "Juegos.html", {
        "nivel": niveles[0],
        "cartas": Carta.objects.filter(nivel=niveles[0]).order_by("posicion")
    })





# -----------------------------
# 📊 ESTADÍSTICAS DEL USUARIO
# -----------------------------
from django.contrib.auth.models import User
from .models import Estadistica

def user_stats(request, username):
    """
    Devuelve estadísticas básicas del jugador en formato JSON.
    """
    user = get_object_or_404(User, username=username)
    stats, _ = Estadistica.objects.get_or_create(usuario=user)

    data = {
        "usuario": user.username,
        "total_partidas": stats.total_partidas,
        "victorias": stats.victorias,
        "derrotas": stats.derrotas,
        "promedio_intentos": stats.promedio_intentos,
    }
    return JsonResponse(data)



# -----------------------------
# 🧾 REGISTRO DE NUEVOS USUARIOS
# -----------------------------
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.shortcuts import render, redirect

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user =save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'✅ ¡Cuenta creada para {username}! Ahora puedes iniciar sesión.')
            return redirect('login')  # ✅ Redirige al login después del registro exitoso

    else:
        form = UserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form})


# -----------------------------
# 🏠 PÁGINA DE INICIO (LANDING)
# -----------------------------
from django.contrib.auth import logout

def landing(request):
    """
    Página pública principal (/).
    Si hay una sesión activa, se cierra antes de mostrar el index.
    """
    if request.user.is_authenticated:
        logout(request)  # ✅ Cierra la sesión automáticamente

    return render(request, 'index.html')






# -----------------------------
# 🧮 ACTUALIZAR ESTADÍSTICA AL GANAR PARTIDA
# -----------------------------
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

@csrf_exempt
def actualizar_estadistica(request):
    """
    Se llama cuando el jugador completa un nivel.
    Actualiza estadísticas y marca la partida como ganada.
    """
    if request.method == 'POST':
        data = json.loads(request.body)
        usuario = request.user
        nivel_nombre = data.get('nivel')
        tiempo = data.get('tiempo', '00:00')
        intentos = data.get('intentos', 0)
        pares = data.get('pares', 0)

        # Validar y convertir datos
        intentos = int(intentos) if str(intentos).isdigit() else 0
        pares = int(pares) if str(pares).isdigit() else 0

        # Buscar nivel y partida activa
        nivel = Nivel.objects.filter(nombre=nivel_nombre).first()
        if not nivel:
            return JsonResponse({'error': 'Nivel no encontrado'}, status=404)

        partida = Partida.objects.filter(usuario=usuario, nivel=nivel, activa=True).first()
        if partida:
            partida.ganada = True
            partida.activa = False
            partida.fecha_fin = timezone.now()
            partida.movimientos = intentos
            partida.aciertos = pares
            partida.save()

        # Buscar o crear estadística del nivel
        estadistica, _ = Estadistica.objects.get_or_create(usuario=usuario, nivel=nivel)
        estadistica.tiempo = tiempo
        estadistica.intentos = intentos
        estadistica.pares_encontrados = pares
        estadistica.total_partidas += 1
        estadistica.victorias += 1
        estadistica.promedio_intentos = (
            (estadistica.promedio_intentos * (estadistica.total_partidas - 1)) + intentos
        ) / estadistica.total_partidas
        estadistica.save()

        return JsonResponse({'status': 'ok'})

    return JsonResponse({'error': 'Método no permitido'}, status=405)





# -----------------------------
# 🎮 TABLERO PRINCIPAL DEL JUEGO
# -----------------------------
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Nivel, Carta, Partida, Estadistica
import random


@login_required
def game_board_view(request):
    from django.utils import timezone
    import random

    # 🔹 Leer nivel de la URL
    nombre_nivel = request.GET.get('nivel', 'Fácil')

    # 🔹 Buscar nivel exacto sin depender de acentos
    nivel = Nivel.objects.filter(nombre__iexact=nombre_nivel).first()
    if not nivel:
        nivel = Nivel.objects.first()

    # 🔹 Cerrar partidas activas previas del usuario
    Partida.objects.filter(usuario=request.user, activa=True).update(activa=False, fecha_fin=timezone.now())

    # 🔹 Crear nueva partida
    partida = Partida.objects.create(
        usuario=request.user,
        nivel=nivel,
        movimientos=0,
        aciertos=0,
        ganada=False,
        activa=True
    )

    # 🔹 Cargar cartas SOLO del nivel actual
    cartas = list(Carta.objects.filter(nivel=nivel))
    if not cartas:
        # Si el nivel no tiene cartas, mostrar mensaje especial
        return render(request, "sin_cartas.html", {"nivel": nivel})

    random.shuffle(cartas)

    # 🔹 Guardar estado en sesión
    request.session['cartas'] = [c.id for c in cartas]
    request.session['revealed'] = []
    request.session['matched'] = []
    request.session['movimientos'] = 0
    request.session['aciertos'] = 0

    # 🔹 Cargar niveles para menú lateral
    niveles = Nivel.objects.all().order_by('dificultad')

    return render(request, 'game_board.html', {
        'nivel': nivel,
        'cartas': cartas,
        'niveles': niveles,
        'partida': partida
    })




















# -----------------------------
# 🟪 CAMBIAR AUTOMÁTICAMENTE AL SIGUIENTE NIVEL
# -----------------------------
def next_level(request):
    niveles = list(Nivel.objects.all().order_by('dificultad'))
    if not niveles:
        return redirect('/game_board/?nivel=Fácil')

    actual_nombre = request.GET.get('nivel', niveles[0].nombre)
    actual_index = next((i for i, n in enumerate(niveles) if n.nombre.lower() == actual_nombre.lower()), -1)

    if actual_index != -1 and actual_index + 1 < len(niveles):
        siguiente = niveles[actual_index + 1]
    else:
        siguiente = niveles[0]  # vuelve al primero si es el último

    # 🔹 Redirige usando el nombre exacto del nivel
    return redirect(f'/game_board/?nivel={siguiente.nombre}')




# -----------------------------
# 🏠 HOME PRINCIPAL
# -----------------------------
@login_required
def home(request):
    user = request.user
    if user.is_superuser:
        return render(request, "home_admin.html", {"user": user})
    return render(request, "home_player.html", {"user": user})



# -----------------------------
# 🧮 REGISTRAR INTENTOS Y ESTADÍSTICAS
# -----------------------------
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from .models import Intento, Estadistica, Nivel

@csrf_exempt
def registrar_intento(request):
    """
    Registra un intento del jugador.
    """
    if request.method == 'POST':
        data = json.loads(request.body)
        usuario = request.user
        correcto = data.get('correcto', False)

        # Guarda un intento en la base de datos
        Intento.objects.create(usuario=usuario, es_correcto=correcto)
        return JsonResponse({'status': 'ok'})
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)










# 📦 Importaciones necesarias al inicio del archivo
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
import json
from django.contrib.auth.models import User
from .models import Partida, Nivel, Carta, Estadistica


@csrf_exempt
def guardar_estadistica(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            usuario_nombre = data.get('usuario')
            nivel_nombre = data.get('nivel')
            pares = int(data.get('pares', 0))
            intentos = int(data.get('intentos', 0))
            tiempo = data.get('tiempo', '00:00')

            usuario = User.objects.get(username=usuario_nombre)
            nivel = Nivel.objects.get(nombre=nivel_nombre)

            # Buscar la última partida activa del usuario en ese nivel
            partida = Partida.objects.filter(usuario=usuario, nivel=nivel, activa=True).last()

            if partida:
                total_cartas = Carta.objects.filter(nivel=nivel).count()
                total_pares = total_cartas // 2

                # Actualizar datos de la partida
                partida.aciertos = pares
                partida.movimientos = intentos

                
                partida.ganada = True if pares >= total_pares and total_pares > 0 else False



                partida.fecha_fin = timezone.now()
                partida.activa = False
                partida.save()

                # Guardar estadística individual
                Estadistica.objects.create(
                    usuario=usuario,
                    nivel=nivel,
                    pares_encontrados=pares,
                    intentos=intentos,
                    tiempo=tiempo
                )

                return JsonResponse({'status': 'ok', 'mensaje': 'Estadística guardada correctamente.'})

            else:
                return JsonResponse({'status': 'error', 'mensaje': 'No se encontró una partida activa.'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'detalle': str(e)})

    return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido'})





from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Estadistica

# -------------------------------
# 📊 VISTA: Estadísticas del jugador
# -------------------------------
@login_required
def estadisticas_usuario(request):
    """Muestra las estadísticas del usuario autenticado."""
    estadisticas = Estadistica.objects.filter(usuario=request.user).select_related('nivel')

    return render(request, 'estadisticas.html', {
        'usuario': request.user,
        'estadisticas': estadisticas
    })



# -----------------------------
# ⏱️ DERROTA POR TIEMPO O ABANDONO
# -----------------------------
from django.views.decorators.csrf import csrf_exempt
from .services.game_engine import forfeit_game

@csrf_exempt
def marcar_derrota(request):
    """
    Marca la partida activa del usuario como derrota.
    Llamada automática si se acaba el tiempo o el jugador abandona.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'No autenticado'}, status=401)

    partida = Partida.objects.filter(usuario=request.user, activa=True).last()
    if not partida:
        return JsonResponse({'error': 'No hay partida activa'}, status=404)

    resultado = forfeit_game(partida)
    return JsonResponse({'status': 'ok', 'detalle': resultado})



