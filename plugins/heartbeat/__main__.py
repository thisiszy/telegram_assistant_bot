from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
import logging

def get_info():
    return {
        "name": "alive", 
        "version": "1.0.0", 
        "author": "thisiszy",
        "description": "*alive*: Use /alive command to check if the bot is alive",
        "commands": ["alive"]
    }

# return handlers list
def get_handlers(command_list):
    info = get_info()
    handlers = [CommandHandler("alive", alive)]
    if "alive" in command_list:
        logging.log(logging.ERROR, f"Command {command} already exists, ignored!")
        return []
    logging.log(logging.INFO, f"Loaded plugin alive, commands: alive")
    return handlers, info

async def alive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Alive!")