from django.contrib import admin
from .models import Nivel, Partida, Carta, Intento, Estadistica


@admin.register(Nivel)
class NivelAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'dificultad')
    search_fields = ('nombre',)
    ordering = ('dificultad',)


@admin.register(Carta)
class CartaAdmin(admin.ModelAdmin):
    list_display = ('identificador', 'nivel')
    list_filter = ('nivel',)
    search_fields = ('identificador',)


@admin.register(Partida)
class PartidaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'nivel', 'fecha_inicio', 'fecha_fin', 'activa', 'ganada', 'movimientos', 'aciertos')
    list_filter = ('activa', 'ganada', 'nivel')
    search_fields = ('usuario__username',)
    ordering = ('-fecha_inicio',)



@admin.register(Intento)
class IntentoAdmin(admin.ModelAdmin):
    list_display = ('partida', 'carta1', 'carta2', 'es_correcto', 'fecha')
    list_filter = ('es_correcto',)
    search_fields = ('partida__usuario__username',)


@admin.register(Estadistica)
class EstadisticaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'total_partidas', 'victorias', 'derrotas', 'promedio_intentos')
    search_fields = ('usuario__username',)


