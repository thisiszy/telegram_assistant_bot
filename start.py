import logging
import configparser
from api import get_handlers
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

help_info = ["No plugins loaded"]

async def help_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="\n".join(help_info), parse_mode="MarkdownV2")

if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read('config.ini')
    token = config['TELEGRAM']['ACCESS_TOKEN']
    application = ApplicationBuilder().token(token).build()
    help_info = get_handlers(application)
    echo_handler = CommandHandler("help", help_message)
    application.add_handler(echo_handler)

    application.run_polling()