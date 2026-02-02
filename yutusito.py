import os
import asyncio
import yt_dlp
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# 1. Configuración
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
YOUR_USERNAME = os.getenv("TELEGRAM_USERNAME")

if not os.path.exists('downloads'):
    os.makedirs('downloads')

# 2. Barra de progreso
def progress_hook(d, msg_espera, loop, context, chat_id):
    if d['status'] == 'downloading':
        p = d.get('_percent_str', '0%')
        mensaje = f"⏳ Descargando: {p}"
        # Solo intentamos editar si el loop sigue vivo
        loop.create_task(context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg_espera.message_id,
            text=mensaje
        ))

# 3. Función de descarga con Miniatura
async def download_audio(url, msg_espera, context, chat_id):
    loop = asyncio.get_event_loop()
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'writethumbnail': True,
        'postprocessors': [
            # Convierte a MP3
            {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'},
            # Asegura que la miniatura sea JPG compatible con Telegram
            {'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'},
            # Pega la miniatura (requiere atomicparsley en el Dockerfile)
            {'key': 'EmbedThumbnail'},
            # Agrega metadatos como Título y Artista
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

# 4. Manejador de mensajes
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.username != YOUR_USERNAME:
        return

    url = update.message.text
    if "youtube.com" not in url and "youtu.be" not in url:
        await update.message.reply_text("❌ Por favor, envía un enlace válido de YouTube.")
        return

    msg_espera = await update.message.reply_text("⏳ Iniciando...")
    ruta_archivo = None

    try:
        ruta_archivo = await download_audio(url, msg_espera, context, update.effective_chat.id)
        
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=msg_espera.message_id,
            text="📤 Subiendo audio con carátula..."
        )

        with open(ruta_archivo, 'rb') as audio:
            await update.message.reply_audio(
                audio=audio,
                title=os.path.basename(ruta_archivo).replace(".mp3", ""),
                caption="✅ ¡Listo! Disfruta tu música"
            )
        
        await msg_espera.delete()

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
    
    finally:
        # Limpieza de archivos temporales en Koyeb
        if ruta_archivo:
            if os.path.exists(ruta_archivo):
                os.remove(ruta_archivo)
            # Borrar miniaturas sobrantes (.jpg, .webp, .png)
            base = os.path.splitext(ruta_archivo)[0]
            for ext in ['.jpg', '.webp', '.png', '.temp.jpg']:
                if os.path.exists(base + ext):
                    os.remove(base + ext)

def main():
    print("🚀 Bot iniciado con soporte para carátulas")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == '__main__':
    main()