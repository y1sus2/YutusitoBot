# Usamos una imagen de Python oficial
FROM python:3.10-slim

# Instalamos FFmpeg dentro del servidor de Koyeb
RUN apt-get update && apt-get install -y ffmpeg && apt-get clean

# Establecemos la carpeta de trabajo
WORKDIR /app

# Copiamos e instalamos las librerías
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto de tu código
COPY . .

# Comando para arrancar el bot
CMD ["python", "mi_bot.py"]