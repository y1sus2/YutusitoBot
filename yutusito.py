import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import yt_dlp

# Cargar las variables del archivo .env
load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
YOUR_USERNAME = os.getenv("TELEGRAM_USERNAME")

async def download_audio(url):
    """Descarga el audio de YouTube usando yt-dlp"""
    output_template = 'downloads/%(title)s.%(ext)s'
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info).replace('.webm', '.mp3').replace('.m4a', '.mp3')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Seguridad: Solo responde a tu usuario
    if update.message.from_user.username != YOUR_USERNAME.replace("@", ""):
        return

    url = update.message.text
    if "youtube.com" in url or "youtu.be" in url:
        msg = await update.message.reply_text("⏳ Procesando audio... dame un momento.")
        
        try:
            file_path = await download_audio(url)
            await update.message.reply_audio(audio=open(file_path, 'rb'))
            os.remove(file_path) # Limpia el archivo para no llenar tu PC
            await msg.delete()
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    else:
        await update.message.reply_text("Envíame un link de YouTube válido.")

def main():
    if not os.path.exists('downloads'): os.makedirs('downloads')
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot encendido... envíame un link por Telegram.")
    app.run_polling()

if __name__ == '__main__':
    main()