import logging
import configparser
import argparse
from pathlib import Path

from telegram import Update
from telegram.ext import ApplicationBuilder, CallbackContext
from telegram.error import NetworkError

from tg_bot.core.handler_helper import add_handlers

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def error(update: Update, context: CallbackContext) -> None:
    """Log Errors caused by Updates."""
    if context.error == NetworkError:
        print("Network error")
    else:
        raise context.error


def main():
    parser = argparse.ArgumentParser(description='Telegram Bot')
    parser.add_argument('--config-dir', type=str, required=True, help='Path to the configuration directory')
    args = parser.parse_args()
    config = configparser.ConfigParser()
    config.read(Path(args.config_dir) / 'config.ini')
    token = config['TELEGRAM']['ACCESS_TOKEN']
    application = ApplicationBuilder().token(token).build()
    add_handlers(application, Path(args.config_dir))

    application.add_error_handler(error)

    application.run_polling()


if __name__ == '__main__':
    main()
