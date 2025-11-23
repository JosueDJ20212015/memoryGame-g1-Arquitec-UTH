# memory_game/services/game_engine.py
import random
from datetime import datetime
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils import timezone

# Importar modelos desde el paquete superior (memory_game.models)
from ..models import (
    Partida as Game,
    Carta as Card,
    Intento as Attempt,
    Nivel as Level,
    Estadistica,
)

# -------------------------------
# FUNCIONES AUXILIARES
# -------------------------------

def _generate_values(card_pairs):
    """Genera identificadores para pares: ['card_0', 'card_1', ...], duplica y baraja."""
    base = [f"card_{i}" for i in range(card_pairs)]
    values = base + base[:]  # duplicar para pares
    random.shuffle(values)
    return values


def _get_card_pairs_from_level(level):
    """Obtiene el número de pares según el modelo Nivel."""
    if level is None:
        return 2
    card_pairs = getattr(level, 'card_pairs', None)
    if card_pairs:
        try:
            return int(card_pairs)
        except Exception:
            pass

    rows = getattr(level, 'rows', None)
    cols = getattr(level, 'cols', None)
    if rows and cols:
        try:
            return (int(rows) * int(cols)) // 2
        except Exception:
            pass

    # Fallback: intentar usar campo 'dificultad' para inferir
    try:
        diff = int(getattr(level, 'dificultad', 1))
        if diff == 1:
            return 6   # 12 cartas
        if diff == 2:
            return 9   # 18 cartas
        if diff >= 3:
            return 12  # 24 cartas
    except Exception:
        pass

    return 2  # valor por defecto


# -------------------------------
# CREAR PARTIDA Y BARAJAR CARTAS
# -------------------------------

def create_game(player, level, meta=None):
    """Crea una partida y sus cartas barajadas."""
    card_pairs = _get_card_pairs_from_level(level)
    total_cards = card_pairs * 2
    values = _generate_values(card_pairs)

    # Cerrar partidas activas previas del usuario
    Game.objects.filter(usuario=player, activa=True).update(
        activa=False, fecha_fin=timezone.now(), ganada=False
    )

    # Crear nueva partida
    game = Game.objects.create(
        usuario=player,
        nivel=level,
        activa=True,
        ganada=False,
        movimientos=0,
        aciertos=0
    )

    # Crear cartas asociadas
    cards = []
    for pos in range(total_cards):
        valor_actual = values[pos]
        cards.append(Card(
            partida=game,
            nivel=level,
            posicion=pos,
            valor=valor_actual,
            simbolo=valor_actual,  # ✅ campo agregado
            revelada=False,
            emparejada=False
        ))
    Card.objects.bulk_create(cards)

    return game


# -------------------------------
# LÓGICA DE JUEGO
# -------------------------------

@transaction.atomic
def reveal_card(game, position):
    """Revela una carta y compara si hay pareja."""
    if not game.activa:
        return {'status': 'error', 'message': 'Partida finalizada'}

    try:
        card = Card.objects.select_for_update().get(partida=game, posicion=position)
    except Card.DoesNotExist:
        return {'status': 'error', 'message': 'Posición inválida'}

    # Si ya está emparejada o revelada, ignorar
    if card.emparejada:
        return {'status': 'ignored', 'message': 'Carta ya emparejada'}
    if card.revelada:
        return {'status': 'ignored', 'message': 'Carta ya revelada'}

    # Revelar carta
    card.revelada = True
    card.save()

    # Buscar otra carta revelada sin emparejar
    other = Card.objects.filter(
        partida=game, revelada=True, emparejada=False
    ).exclude(posicion=position).first()

    if not other:
        # Solo una carta revelada
        return {
            'status': 'first_reveal',
            'posicion': card.posicion,
            'valor': card.valor,
            'simbolo': card.simbolo,
            'estado_partida': serialize_game_state(game)
        }

    # Dos cartas reveladas → comparar
    game.movimientos += 1
    es_par = (other.valor == card.valor)

    if es_par:
        other.emparejada = True
        card.emparejada = True
        other.save()
        card.save()

        # ✅ Guardar el acierto inmediatamente
        game.aciertos += 1
        game.save(update_fields=["aciertos"])

        Attempt.objects.create(partida=game, carta1=other, carta2=card, es_correcto=True)
    else:
        Attempt.objects.create(partida=game, carta1=other, carta2=card, es_correcto=False)

    # Verificar si ganó
    total_pairs = _get_card_pairs_from_level(game.nivel)
    if game.aciertos >= total_pairs:
        game.activa = False
        game.ganada = True
        game.fecha_fin = timezone.now()
        actualizar_estadisticas(game)

    game.save()

    return {
        'status': 'checked',
        'acierto': es_par,
        'posiciones': [other.posicion, card.posicion],
        'valores': [other.valor, card.valor],
        'simbolos': [other.simbolo, card.simbolo],
        'estado_partida': serialize_game_state(game)
    }


# -------------------------------
# OCULTAR CARTAS INCORRECTAS
# -------------------------------

@transaction.atomic
def hide_unmatched(game, pos1, pos2):
    """Oculta dos cartas que no hicieron par (usado por la vista/JS tras timeout)."""
    cards = list(Card.objects.select_for_update().filter(
        partida=game, posicion__in=[pos1, pos2]
    ))
    ocultadas = []
    for c in cards:
        if not c.emparejada:
            c.revelada = False
            c.save()
            ocultadas.append(c.posicion)
    return {'status': 'ok', 'ocultadas': ocultadas, 'estado_partida': serialize_game_state(game)}


# -------------------------------
# ABANDONAR PARTIDA
# -------------------------------

@transaction.atomic
def forfeit_game(game):
    """
    Marca la partida como derrota y actualiza las estadísticas.
    """
    if not game or not game.activa:
        return "Partida inválida o ya finalizada"

    game.activa = False
    game.ganada = False
    game.fecha_fin = timezone.now()
    game.save()

    stats, _ = Estadistica.objects.get_or_create(usuario=game.usuario, nivel=game.nivel)
    stats.total_partidas += 1
    stats.derrotas += 1
    stats.save()
    return "Partida marcada como derrota"



# -------------------------------
# SERIALIZAR ESTADO
# -------------------------------

def serialize_game_state(game):
    """Devuelve el estado actual de la partida con campos necesarios para el cliente."""
    cards_qs = game.carta_set.all().order_by('posicion')
    cards_list = []

    for c in cards_qs:
        item = {
            'posicion': c.posicion,
            'revelada': c.revelada,
            'emparejada': c.emparejada,
            'valor': c.valor if (c.revelada or c.emparejada) else None,
            'simbolo': c.simbolo if (c.revelada or c.emparejada) else None,
        }
        cards_list.append(item)

    return {
        'partida_id': str(game.id),
        'movimientos': game.movimientos,
        'aciertos': game.aciertos,
        'activa': game.activa,
        'ganada': game.ganada,
        'cartas': cards_list,
    }

# -------------------------------
# ACTUALIZAR ESTADÍSTICAS
# -------------------------------
def actualizar_estadisticas(game):
    """Actualiza las estadísticas del usuario y nivel al finalizar una partida."""
    stats, _ = Estadistica.objects.get_or_create(
        usuario=game.usuario,
        nivel=game.nivel
    )

    # 🔹 Incrementar partidas totales
    stats.total_partidas += 1

    # 🔹 Registrar victoria o derrota
    if game.ganada:
        stats.victorias += 1
    else:
        stats.derrotas += 1

    # 🔹 Calcular promedio de intentos
    intentos = game.movimientos or 0
    if stats.total_partidas > 0:
        promedio = (
            ((stats.promedio_intentos * (stats.total_partidas - 1)) + intentos)
            / stats.total_partidas
        )
        stats.promedio_intentos = round(promedio, 2)

    stats.save()



# -------------------------------
# Vista auxiliar para AJAX
# -------------------------------

@login_required
def reveal_card_view(request, pos):
    """Endpoint GET para revelar carta por posición (URL: /reveal/<pos>/)."""
    partida = Game.objects.filter(usuario=request.user, activa=True).first()
    if not partida:
        return JsonResponse({'status': 'error', 'message': 'No hay partida activa'}, status=400)

    resultado = reveal_card(partida, pos)
    resultado["aciertos_actuales"] = partida.aciertos

    return JsonResponse(resultado)
