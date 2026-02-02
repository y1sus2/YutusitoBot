# Usar una imagen de Python ligera
FROM python:3.10-slim

# Instalar dependencias del sistema: ffmpeg y atomicparsley
RUN apt-get update && apt-get install -y \
    ffmpeg \
    atomicparsley \
    && rm -rf /var/lib/apt/lists/*

# Establecer directorio de trabajo
WORKDIR /app

# Copiar archivos del proyecto
COPY . .

# Instalar librerías de Python
RUN pip install --no-cache-dir -r requirements.txt

# Comando para ejecutar el bot
CMD ["python", "yutusito.py"]