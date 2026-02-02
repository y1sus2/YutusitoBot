import os
import asyncio
import yt_dlp
import shutil
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

# 1. Configuración
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
YOUR_USERNAME = os.getenv("TELEGRAM_USERNAME")

if not os.path.exists('downloads'):
    os.makedirs('downloads')

# 2. Comando /espacio para verificar el almacenamiento
async def espacio_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.username != YOUR_USERNAME:
        return
    
    # Obtenemos estadísticas del disco en la carpeta raíz
    total, usado, libre = shutil.disk_usage("/")
    
    # Convertimos a GB para que sea fácil de leer
    libre_gb = libre / (2**30)
    usado_gb = usado / (2**30)
    
    mensaje = (
        f"📊 **Estado del Servidor (Koyeb)**\n\n"
        f"✅ Espacio libre: {libre_gb:.2f} GB\n"
        f"⚠️ Espacio usado: {usado_gb:.2f} GB\n\n"
        f"El bot borra todo automáticamente después de cada descarga."
    )
    await update.message.reply_text(mensaje, parse_mode='Markdown')

# 3. Barra de progreso
def progress_hook(d, msg_espera, loop, context, chat_id):
    if d['status'] == 'downloading':
        p = d.get('_percent_str', '0%')
        mensaje = f"⏳ Descargando: {p}"
        loop.create_task(context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg_espera.message_id,
            text=mensaje
        ))

# 4. Función de descarga corregida
async def download_audio(url, msg_espera, context, chat_id):
    loop = asyncio.get_event_loop()
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'writethumbnail': True,
        'postprocessors': [
            {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'},
            {'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'},
            {'key': 'EmbedThumbnail'},
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

# 5. Manejador de mensajes con filtro de 30 minutos
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.username != YOUR_USERNAME:
        return

    url = update.message.text
    if "youtube.com" not in url and "youtu.be" not in url:
        return

    # Extraer información sin descargar para chequear la duración
    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            duracion_segundos = info.get('duration', 0)
            
            # REGLA DE LOS 30 MINUTOS (1800 segundos)
            if duracion_segundos > 1800:
                await update.message.reply_text("Disculpe su video dura más de 30min y no podemos descargarlo")
                return

    except Exception as e:
        await update.message.reply_text(f"❌ Error al verificar el video: {str(e)}")
        return

    msg_espera = await update.message.reply_text("⏳ Iniciando descarga...")
    ruta_archivo = None

    try:
        ruta_archivo = await download_audio(url, msg_espera, context, update.effective_chat.id)
        
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=msg_espera.message_id,
            text="📤 Subiendo audio..."
        )

        with open(ruta_archivo, 'rb') as audio:
            await update.message.reply_audio(
                audio=audio,
                title=os.path.basename(ruta_archivo).replace(".mp3", ""),
                caption="✅ ¡Listo!"
            )
        
        await msg_espera.delete()

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
    
    finally:
        if ruta_archivo:
            if os.path.exists(ruta_archivo):
                os.remove(ruta_archivo)
            base = os.path.splitext(ruta_archivo)[0]
            for ext in ['.jpg', '.webp', '.png', '.temp.jpg']:
                if os.path.exists(base + ext):
                    os.remove(base + ext)

def main():
    print("🚀 YutusitoBot v3.0 - Filtro 30min y comando /espacio activos.")
    app = Application.builder().token(TOKEN).build()
    
    # Añadimos el comando /espacio
    app.add_handler(CommandHandler("espacio", espacio_comando))
    
    # Manejador de enlaces
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app.run_polling()

if __name__ == '__main__':
    main()