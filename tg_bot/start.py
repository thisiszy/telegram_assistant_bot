import logging
import configparser
from tg_bot.core.handler_helper import add_handlers

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackContext
from telegram.error import NetworkError

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

help_info = ["No plugins loaded"]

def error(update: Update, context: CallbackContext) -> None:
    """Log Errors caused by Updates."""
    if context.error == NetworkError:
        print("Network error")
    else:
        raise context.error


def main():
    config = configparser.ConfigParser()
    config.read('tg_bot/configs/config.ini')
    token = config['TELEGRAM']['ACCESS_TOKEN']
    application = ApplicationBuilder().token(token).build()
    add_handlers(application)

    application.add_error_handler(error)

    application.run_polling()


if __name__ == '__main__':
    main()