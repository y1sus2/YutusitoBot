import os
import asyncio
import yt_dlp
import shutil
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

# 1. Configuración Inicial
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_USERNAME = os.getenv("TELEGRAM_USERNAME") # Variable unificada

if not os.path.exists('downloads'):
    os.makedirs('downloads')

# 2. Comando /espacio para verificar almacenamiento
async def espacio_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Verificación de seguridad con el nombre correcto
    if update.message.from_user.username != TELEGRAM_USERNAME:
        return
    
    # Cálculo de espacio en disco en Koyeb
    total, usado, libre = shutil.disk_usage("/")
    libre_gb = libre / (2**30)
    usado_gb = usado / (2**30)
    
    mensaje = (
        f"📊 **Estado del Servidor (Koyeb)**\n\n"
        f"✅ Espacio libre: {libre_gb:.2f} GB\n"
        f"⚠️ Espacio usado: {usado_gb:.2f} GB\n\n"
        f"El bot limpia automáticamente los archivos después de cada envío."
    )
    await update.message.reply_text(mensaje, parse_mode='Markdown')

# 3. Barra de progreso dinámica
def progress_hook(d, msg_espera, loop, context, chat_id):
    if d['status'] == 'downloading':
        p = d.get('_percent_str', '0%')
        mensaje = f"⏳ Descargando: {p}"
        # Intentar editar el mensaje para mostrar el avance
        loop.create_task(context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg_espera.message_id,
            text=mensaje
        ))

# 4. Función principal de descarga y procesamiento
async def download_audio(url, msg_espera, context, chat_id):
    loop = asyncio.get_event_loop()
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'writethumbnail': True,
        'postprocessors': [
            # Extraer audio MP3
            {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'},
            # Convertir miniatura a JPG para Telegram
            {'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'},
            # Incrustar miniatura (requiere atomicparsley en Dockerfile)
            {'key': 'EmbedThumbnail'},
            # Añadir metadatos
            {'key': 'FFmpegMetadata', 'add_metadata': True},
        ],
        'progress_hooks': [lambda d: progress_hook(d, msg_espera, loop, context, chat_id)],
        'quiet': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        archivo_base = ydl.prepare_filename(info)
        ruta_mp3 = os.path.splitext(archivo_base)[0] + ".mp3"
        return ruta_mp3

# 5. Manejador de enlaces con filtro de 30 minutos
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Verificación de seguridad
    if update.message.from_user.username != TELEGRAM_USERNAME:
        return

    url = update.message.text
    if "youtube.com" not in url and "youtu.be" not in url:
        return

    # Verificar duración antes de descargar para proteger la RAM de Koyeb
    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            duracion_segundos = info.get('duration', 0)
            
            if duracion_segundos > 1800: # Límite de 30 minutos
                await update.message.reply_text("Disculpe su video dura más de 30min y no podemos descargarlo")
                return

    except Exception as e:
        await update.message.reply_text(f"❌ Error al analizar el video: {str(e)}")
        return

    msg_espera = await update.message.reply_text("⏳ Preparando descarga...")
    ruta_archivo = None

    try:
        ruta_archivo = await download_audio(url, msg_espera, context, update.effective_chat.id)
        
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=msg_espera.message_id,
            text="📤 Enviando audio con carátula..."
        )

        with open(ruta_archivo, 'rb') as audio:
            await update.message.reply_audio(
                audio=audio,
                title=os.path.basename(ruta_archivo).replace(".mp3", ""),
                caption="✅ ¡Disfruta tu música!"
            )
        
        await msg_espera.delete()

    except Exception as e:
        await update.message.reply_text(f"❌ Error en la descarga: {str(e)}")
    
    finally:
        # Limpieza profunda de archivos para no agotar los 2GB de Koyeb
        if ruta_archivo:
            if os.path.exists(ruta_archivo):
                os.remove(ruta_archivo)
            base = os.path.splitext(ruta_archivo)[0]
            for ext in ['.jpg', '.webp', '.png', '.temp.jpg']:
                if os.path.exists(base + ext):
                    os.remove(base + ext)

# 6. Ejecución del Bot
def main():
    if not TOKEN:
        print("Error: No se encontró el TOKEN de Telegram.")
        return
    
    print(f"🚀 Bot iniciado para el usuario: {TELEGRAM_USERNAME}")
    app = Application.builder().token(TOKEN).build()
    
    # Importante: Registrar el comando antes que el manejador de texto
    app.add_handler(CommandHandler("espacio", espacio_comando))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app.run_polling()

if __name__ == '__main__':
    main()