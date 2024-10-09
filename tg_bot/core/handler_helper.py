from tg_bot.core.api import get_handlers
from tg_bot.core.help import Help

from telegram.ext import CommandHandler, Application

def add_handlers(application: Application):
    help_info = get_handlers(application)
    help = Help(help_info)
    echo_handler = CommandHandler("help", help.help_message)
    application.add_handler(echo_handler)
