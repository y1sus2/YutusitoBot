import os
import asyncio
import yt_dlp
import shutil
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

# 1. Configuración e Inicialización de Archivo de Usuarios
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
OWNER = os.getenv("TELEGRAM_USERNAME") # Tu usuario (El Jefe)
USER_FILE = "usuarios_permitidos.txt"

# Crear el archivo si no existe y añadirte a ti por defecto
if not os.path.exists(USER_FILE):
    with open(USER_FILE, "w") as f:
        f.write(f"{OWNER}\n")

def obtener_usuarios():
    with open(USER_FILE, "r") as f:
        return [line.strip() for line in f.readlines() if line.strip()]

if not os.path.exists('downloads'):
    os.makedirs('downloads')

# 2. COMANDOS DE ADMINISTRACIÓN (Solo para el OWNER)
async def gestion_usuarios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_actual = update.message.from_user.username
    if user_actual != OWNER:
        return

    lista = obtener_usuarios()
    msg = "👥 **Usuarios con acceso:**\n\n"
    for u in lista:
        # Resaltar quién es el dueño
        msg += f"• `{u}` {'(Dueño)' if u == OWNER else ''}\n"
    
    msg += "\n**Comandos:**\n`/add nombre` - Añadir\n`/del nombre` - Eliminar"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def añadir_usuario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.username != OWNER: return
    
    if not context.args:
        await update.message.reply_text("Uso: `/add nombre_de_usuario` (sin @)", parse_mode='Markdown')
        return

    nuevo = context.args[0].replace("@", "")
    usuarios = obtener_usuarios()
    
    if nuevo not in usuarios:
        with open(USER_FILE, "a") as f:
            f.write(f"{nuevo}\n")
        await update.message.reply_text(f"✅ `{nuevo}` ha sido autorizado.", parse_mode='Markdown')
    else:
        await update.message.reply_text("Ese usuario ya tiene acceso.")

async def eliminar_usuario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.username != OWNER: return
    
    if not context.args:
        await update.message.reply_text("Uso: `/del nombre_de_usuario` (sin @)", parse_mode='Markdown')
        return

    blanco = context.args[0].replace("@", "")
    if blanco == OWNER:
        await update.message.reply_text("No puedes eliminarte a ti mismo (dueño).")
        return

    usuarios = obtener_usuarios()
    if blanco in usuarios:
        usuarios.remove(blanco)
        with open(USER_FILE, "w") as f:
            for u in usuarios: f.write(f"{u}\n")
        await update.message.reply_text(f"❌ `{blanco}` ha sido eliminado.")
    else:
        await update.message.reply_text("Usuario no encontrado.")

# 3. COMANDO ESPACIO
async def espacio_comando(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.username not in obtener_usuarios(): return
    total, usado, libre = shutil.disk_usage("/")
    libre_gb = libre / (2**30)
    await update.message.reply_text(f"📊 Espacio libre en servidor: {libre_gb:.2f} GB")

# 4. LOGICA DE DESCARGA (Igual que antes)
def progress_hook(d, msg_espera, loop, context, chat_id):
    if d['status'] == 'downloading':
        p = d.get('_percent_str', '0%')
        loop.create_task(context.bot.edit_message_text(chat_id=chat_id, message_id=msg_espera.message_id, text=f"⏳ Descargando: {p}"))

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
        ruta_mp3 = os.path.splitext(ydl.prepare_filename(info))[0] + ".mp3"
        return ruta_mp3

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # SOLO usuarios en la lista pueden descargar
    if update.message.from_user.username not in obtener_usuarios():
        return

    url = update.message.text
    if "youtube.com" not in url and "youtu.be" not in url: return

    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            if info.get('duration', 0) > 1800:
                await update.message.reply_text("Disculpe su video dura más de 30min y no podemos descargarlo")
                return
    except: return

    msg_espera = await update.message.reply_text("⏳ Preparando...")
    ruta_archivo = None
    try:
        ruta_archivo = await download_audio(url, msg_espera, context, update.effective_chat.id)
        with open(ruta_archivo, 'rb') as audio:
            await update.message.reply_audio(audio=audio, title=os.path.basename(ruta_archivo).replace(".mp3", ""))
        await msg_espera.delete()
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
    finally:
        if ruta_archivo and os.path.exists(ruta_archivo):
            os.remove(ruta_archivo)
            base = os.path.splitext(ruta_archivo)[0]
            for ext in ['.jpg', '.webp', '.png', '.temp.jpg']:
                if os.path.exists(base + ext): os.remove(base + ext)

def main():
    print(f"🚀 Panel de Control activo. Dueño: {OWNER}")
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("users", gestion_usuarios))
    app.add_handler(CommandHandler("add", añadir_usuario))
    app.add_handler(CommandHandler("del", eliminar_usuario))
    app.add_handler(CommandHandler("espacio", espacio_comando))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app.run_polling()

if __name__ == '__main__':
    main()