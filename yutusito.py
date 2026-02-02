import os
import asyncio
import yt_dlp
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# 1. Cargar configuración
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
YOUR_USERNAME = os.getenv("TELEGRAM_USERNAME")

# Crear carpeta de descargas si no existe
if not os.path.exists('downloads'):
    os.makedirs('downloads')

# 2. Función para descargar el audio
async def download_audio(url):
    output_template = 'downloads/%(title)s.%(ext)s'
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        # Obtenemos la ruta final del archivo MP3
        archivo_base = ydl.prepare_filename(info)
        ruta_mp3 = os.path.splitext(archivo_base)[0] + ".mp3"
        return ruta_mp3

# 3. Manejador de mensajes con LIMPIEZA AUTOMÁTICA
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Seguridad: Solo tú puedes usar el bot
    if update.message.from_user.username != YOUR_USERNAME:
        await update.message.reply_text("Acceso denegado.")
        return

    url = update.message.text
    if "youtube.com" not in url and "youtu.be" not in url:
        await update.message.reply_text("Por favor, envía un enlace válido de YouTube.")
        return

    msg_espera = await update.message.reply_text("⏳ Procesando audio... esto puede tardar un momento.")
    ruta_archivo = None

    try:
        # Descarga
        ruta_archivo = await download_audio(url)
        
        # Enviar a Telegram
        with open(ruta_archivo, 'rb') as audio:
            await update.message.reply_audio(
                audio=audio, 
                title=os.path.basename(ruta_archivo).replace(".mp3", ""),
                caption="✅ ¡Aquí tienes tu música!"
            )
        
        await msg_espera.delete()
        print(f"✅ Enviado con éxito: {ruta_archivo}")

    except Exception as e:
        await update.message.reply_text(f"❌ Error al procesar: {str(e)}")
        print(f"Error: {e}")

    finally:
        # LIMPIEZA: Se ejecuta pase lo que pase para ahorrar espacio en Koyeb
        if ruta_archivo and os.path.exists(ruta_archivo):
            try:
                os.remove(ruta_archivo)
                print(f"🗑️ Espacio liberado: {ruta_archivo} eliminado del servidor.")
            except Exception as e:
                print(f"No se pudo eliminar el archivo: {e}")

# 4. Configuración principal
def main():
    if not TOKEN:
        print("Error: No se encontró TELEGRAM_TOKEN en las variables de entorno.")
        return

    print("🚀 Bot encendido y listo en Koyeb... esperando enlaces.")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == '__main__':
    main()