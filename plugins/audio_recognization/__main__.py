from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, filters, ConversationHandler, MessageHandler
import logging
import whisper
import os
import shutil
AUDIO_FILE_PATH = "env/share/whisper/audio"

if os.path.exists(AUDIO_FILE_PATH):
    shutil.rmtree(AUDIO_FILE_PATH)
os.makedirs(AUDIO_FILE_PATH)

def get_info():
    return {
        "name": "audio_recognization", 
        "version": "1.0.0", 
        "author": "thisiszy",
        "description": "*audio\_recognization*: Convert audio to text, use /voice to start, use /stopvoice to stop",
        "commands": [],
        "message_type": ["audio"]
    }

RUNNING = 1

def get_handlers(command_list):
    info = get_info()
    handlers = [ConversationHandler(
        entry_points=[CommandHandler("voice", start)],
        states={
            RUNNING: [MessageHandler(filters.VOICE, convert_audio2text)],
        },
        fallbacks=[CommandHandler("stopvoice", cancel)],
    )]
    logging.log(logging.INFO, f"Loaded plugin {info['name']}, commands: {info['commands']}, message_type: {info['message_type']}")
    return handlers, info

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Now you can send me the voice message, and I will convert it to text.\n\n"
    )
    return RUNNING

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    await update.message.reply_text(
        "Bye! Stop converting audio to text."
    )
    return ConversationHandler.END

async def convert_audio2text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.voice is not None:
        try:
            file = await update.message.voice.get_file()
            audio_file_path = os.path.join(AUDIO_FILE_PATH, file.file_id)
            await file.download_to_drive(audio_file_path)
            logging.log(logging.INFO, f"Received audio file: {audio_file_path}")
            place_holder = await context.bot.send_message(chat_id=update.effective_chat.id, text="Converting...", reply_to_message_id=update.message.message_id)
            model = whisper.load_model("small", download_root="env/share/whisper")
            result = model.transcribe(audio_file_path)
            logging.log(logging.INFO, f"Recognized text: {result['text']}")
            await context.bot.edit_message_text(
                chat_id=place_holder.chat_id, message_id=place_holder.message_id, text=result["text"]
            )
        except Exception as e:
            logging.log(logging.ERROR, f"Error: {e}")
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Error {e}", reply_to_message_id=update.message.message_id)
    return RUNNING
