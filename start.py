import logging
import configparser
from api import get_handlers
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackContext
from telegram.error import NetworkError

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

help_info = ["No plugins loaded"]

async def help_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="\n".join(help_info), parse_mode="MarkdownV2")


def error(update: Update, context: CallbackContext) -> None:
    """Log Errors caused by Updates."""
    if context.error == NetworkError:
        print("Network error")
    else:
        raise context.error

if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read('config.ini')
    token = config['TELEGRAM']['ACCESS_TOKEN']
    application = ApplicationBuilder().token(token).build()
    help_info = get_handlers(application)
    echo_handler = CommandHandler("help", help_message)
    application.add_handler(echo_handler)
    
    application.add_error_handler(error)

    application.run_polling()