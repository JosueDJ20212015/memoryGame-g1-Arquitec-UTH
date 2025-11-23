from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# -------------------------------
# MODELO: NIVEL
# -------------------------------
class Nivel(models.Model):
    nombre = models.CharField(max_length=50)
    dificultad = models.IntegerField(default=1)
    filas = models.IntegerField(default=2)
    columnas = models.IntegerField(default=2)

    def __str__(self):
        return f"{self.nombre} ({self.filas}x{self.columnas})"


# -------------------------------
# MODELO: CARTA
# -------------------------------
class Carta(models.Model):
    partida = models.ForeignKey('Partida', on_delete=models.CASCADE, null=True, blank=True)
    nivel = models.ForeignKey('Nivel', on_delete=models.CASCADE)
    identificador = models.CharField(max_length=100, null=True, blank=True)
    nombre = models.CharField(max_length=100, null=True, blank=True)
    simbolo = models.CharField(max_length=10, null=True, blank=True)
    posicion = models.IntegerField()
    valor = models.CharField(max_length=100, null=True, blank=True)
    revelada = models.BooleanField(default=False)
    emparejada = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.simbolo or '❓'} ({self.nivel.nombre})"


# -------------------------------
# MODELO: PARTIDA
# -------------------------------
class Partida(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    nivel = models.ForeignKey(Nivel, on_delete=models.CASCADE)
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    activa = models.BooleanField(default=True)
    ganada = models.BooleanField(default=False)
    movimientos = models.IntegerField(default=0)
    aciertos = models.IntegerField(default=0)
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Partida de {self.usuario.username} - Nivel {self.nivel.nombre}"

    def finalizar(self, ganada=True):
        self.ganada = ganada
        self.activa = False
        self.fecha_fin = timezone.now()
        self.save()


# -------------------------------
# MODELO: INTENTO
# -------------------------------
class Intento(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    partida = models.ForeignKey('Partida', on_delete=models.CASCADE, null=True, blank=True)
    carta1 = models.ForeignKey('Carta', on_delete=models.CASCADE, related_name='carta1', null=True, blank=True)
    carta2 = models.ForeignKey('Carta', on_delete=models.CASCADE, related_name='carta2', null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    es_correcto = models.BooleanField(default=False)

    def __str__(self):
        return f"Intento de {self.usuario.username if self.usuario else 'Desconocido'} - {'Correcto' if self.es_correcto else 'Fallido'}"



# -------------------------------
# MODELO: ESTADISTICA
# -------------------------------
class Estadistica(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    nivel = models.ForeignKey('Nivel', on_delete=models.CASCADE, null=True, blank=True)
    tiempo = models.CharField(max_length=10, default="00:00")
    intentos = models.IntegerField(default=0)
    pares_encontrados = models.IntegerField(default=0)
    total_partidas = models.IntegerField(default=0)
    victorias = models.IntegerField(default=0)
    derrotas = models.IntegerField(default=0)
    promedio_intentos = models.FloatField(default=0.0)

    def __str__(self):
        return f"{self.usuario.username if self.usuario else 'Desconocido'} - {self.nivel.nombre if self.nivel else 'Sin nivel'}"


