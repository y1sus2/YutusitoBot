import os
import asyncio
import yt_dlp
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# 1. Configuración inicial
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
YOUR_USERNAME = os.getenv("TELEGRAM_USERNAME")

if not os.path.exists('downloads'):
    os.makedirs('downloads')

# 2. Barra de progreso dinámica
def progress_hook(d, msg_espera, loop, context, chat_id):
    if d['status'] == 'downloading':
        p = d.get('_percent_str', '0%')
        # Intentamos editar el mensaje solo si es necesario para evitar bloqueos de Telegram
        mensaje = f"⏳ Descargando: {p}"
        loop.create_task(context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg_espera.message_id,
            text=mensaje
        ))

# 3. Función de descarga con Miniatura Forzada (JPG)
async def download_audio(url, msg_espera, context, chat_id):
    loop = asyncio.get_event_loop()
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'writethumbnail': True, # Descarga la imagen
        'postprocessors': [
            # Extraer el audio primero
            {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'},
            # CONVERTIR MINIATURA A JPG (Crucial para Telegram)
            {'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'},
            # Incrustar la imagen y los metadatos
            {'key': 'EmbedThumbnail'},
            {'key': 'FFmpegMetadata'},
        ],
        'progress_hooks': [lambda d: progress_hook(d, msg_espera, loop, context, chat_id)],
        'quiet': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        archivo_base = ydl.prepare_filename(info)
        # La ruta final será .mp3 tras el procesamiento de FFmpeg
        ruta_mp3 = os.path.splitext(archivo_base)[0] + ".mp3"
        return ruta_mp3

# 4. Manejador de mensajes con Limpieza Profunda
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.username != YOUR_USERNAME:
        return

    url = update.message.text
    if "youtube.com" not in url and "youtu.be" not in url:
        await update.message.reply_text("❌ Por favor, envía un link de YouTube válido.")
        return

    msg_espera = await update.message.reply_text("⏳ Preparando descarga...")
    ruta_archivo = None

    try:
        # Descarga y procesamiento
        ruta_archivo = await download_audio(url, msg_espera, context, update.effective_chat.id)
        
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=msg_espera.message_id,
            text="📤 Enviando audio con carátula..."
        )

        # Envío a Telegram
        with open(ruta_archivo, 'rb') as audio:
            await update.message.reply_audio(
                audio=audio,
                title=os.path.basename(ruta_archivo).replace(".mp3", ""),
                caption="✅ ¡Música lista!"
            )
        
        await msg_espera.delete()

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
    
    finally:
        # LIMPIEZA TOTAL EN KOYEB (Para no agotar los 2GB de disco)
        if ruta_archivo:
            # Borrar MP3
            if os.path.exists(ruta_archivo):
                os.remove(ruta_archivo)
            
            # Borrar cualquier imagen temporal (.jpg o .webp)
            base = os.path.splitext(ruta_archivo)[0]
            for ext in ['.jpg', '.webp', '.png']:
                if os.path.exists(base + ext):
                    os.remove(base + ext)

def main():
    if not TOKEN:
        print("Error: No se encontró el TOKEN.")
        return
    
    print("🚀 YutusitoBot v2.0 Activo - Carátulas y Progreso habilitados.")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == '__main__':
    main()