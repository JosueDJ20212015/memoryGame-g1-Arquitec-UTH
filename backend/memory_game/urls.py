from django.urls import path
from . import views
from .services import game_engine

urlpatterns = [

    
    # Tablero y vistas
    #path('game_board/', views.game_board_view, name='game_board'),
    path('game/reveal/<int:pos>/', views.reveal_card, name='reveal_card'),
    


    path('game/next_level/', views.next_level, name='next_level'),
    path("game/actualizar_estadistica/", views.actualizar_estadistica, name="actualizar_estadistica"),

    # API / lógica del juego
    path('reveal/<int:pos>/', game_engine.reveal_card_view, name='reveal_card'),
    path('new/', views.new_game, name='new_game'),
    path('hide/', views.hide, name='hide'),
    path('state/<int:partida_id>/', views.game_state, name='game_state'),
    path('stats/<str:username>/', views.user_stats, name='user_stats'),

    # Autenticación
    
   
    path('register/', views.register, name='register'),



    path('registrar_intento/', views.registrar_intento, name='registrar_intento'),
    path('guardar_estadistica/', views.guardar_estadistica, name='guardar_estadistica'),
    path('marcar_derrota/', views.marcar_derrota, name='marcar_derrota'),


    
    path('estadisticas/', views.estadisticas_usuario, name='estadisticas_usuario'),



]

