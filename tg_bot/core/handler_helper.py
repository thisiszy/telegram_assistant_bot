from tg_bot.core.api import get_handlers
from tg_bot.core.help import Help
from tg_bot.core.auth import Auth

from telegram.ext import CommandHandler, Application

def add_handlers(application: Application):
    help_msg = get_handlers(application)
    help = Help(help_msg)
    echo_handler = CommandHandler("help", help.help_message)
    application.add_handler(echo_handler)

    auth = Auth()
    add_permission_handler = CommandHandler("add_permission", auth.add_permission)
    application.add_handler(add_permission_handler)
    revoke_permission_handler = CommandHandler("revoke_permission", auth.revoke_permission)
    application.add_handler(revoke_permission_handler)
    list_permissions_handler = CommandHandler("list_permissions", auth.list_permissions)
    application.add_handler(list_permissions_handler)
