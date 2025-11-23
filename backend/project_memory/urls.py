# project_memory/urls.py
from django.contrib import admin
from django.urls import path, include
from memory_game import views as mg_views  

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('memory_game.urls')),
    path('game/', include('memory_game.urls')),

    path('', mg_views.landing, name='landing'),
    path('home/', mg_views.home, name='home'),
    
    path('game_board/', mg_views.game_board_view, name='game_board'),

    path('accounts/', include('allauth.urls')),
]
