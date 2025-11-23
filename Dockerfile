FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

#copiar requirements desde la raíz
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

#copiar todo el contenido de backend a /app
COPY backend/ .

#colectar archivos estáticos (CSS del admin+  sonidos
RUN python manage.py collectstatic --noinput

# exponer puerto
EXPOSE 8000

CMD ["gunicorn", "project_memory.wsgi:application", "--bind", "0.0.0.0:8000"]
