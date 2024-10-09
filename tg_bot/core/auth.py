from functools import wraps
import json
import logging

from telegram import Update
from telegram.ext import ContextTypes

from tg_bot.utils.consts import PERMISSION_TABLE_PATH
from tg_bot.core.handler import command_handler, Handler

logger = logging.getLogger(__name__)

PERMISSION_TABLE_PATH.parent.mkdir(parents=True, exist_ok=True)
if not PERMISSION_TABLE_PATH.exists():
    PERMISSION_TABLE_PATH.touch()
PERMISSION_TABLE = json.load(open(PERMISSION_TABLE_PATH))


def restricted(func):
    @wraps(func)
    async def wrapped(cls, update, context, *args, **kwargs):
        user_id = str(update.effective_user.id)
        if user_id in PERMISSION_TABLE and func.__name__ in PERMISSION_TABLE[user_id]:
            return await func(cls, update, context, *args, **kwargs)
        else:
            logger.error(f"[Unauthorized access] {user_id} tried to access {func.__name__}")
            return await update.message.reply_text("Unauthorized access denied")
    return wrapped


class Auth(Handler):
    @property
    def info(self):
        return {
            "name": "auth",
            "description": "Authentication and authorization",
            "commands": [
                {"command": "add_permission",
                    "description": "Add a permission to a user"},
                {"command": "revoke_permission",
                    "description": "Revoke a permission from a user"},
                {"command": "list_permissions",
                    "description": "List all permissions for a user"}
            ]
        }

    @command_handler
    @restricted
    async def add_permission(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) != 2:
            await update.message.reply_text(r"Usage: /add_permission <permission> <user_id>")
            return
        user_id = context.args[0]
        permission = context.args[1]
        if user_id not in PERMISSION_TABLE:
            PERMISSION_TABLE[user_id] = []
        if permission in PERMISSION_TABLE[user_id]:
            await update.message.reply_text(f"Permission {permission} already added for {user_id}")
        else:
            PERMISSION_TABLE[user_id].append(permission)
            logger.debug(f"New permission table: {PERMISSION_TABLE}")
            logger.info(f"Permission {permission} added for {user_id}")
            json.dump(PERMISSION_TABLE, open(PERMISSION_TABLE_PATH, "w"), indent=4)
            await update.message.reply_text(f"Permission {permission} added for {user_id}")

    @command_handler
    @restricted
    async def revoke_permission(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) != 2:
            await update.message.reply_text(r"Usage: /revoke_permission <permission> <user_id>")
            return
        user_id = context.args[0]
        permission = context.args[1]
        if user_id not in PERMISSION_TABLE:
            await update.message.reply_text(f"User {user_id} not found")
        elif permission in PERMISSION_TABLE[user_id]:
            PERMISSION_TABLE[user_id].remove(permission)
            logger.debug(f"New permission table: {PERMISSION_TABLE}")
            logger.info(f"Permission {permission} revoked for {user_id}")
            json.dump(PERMISSION_TABLE, open(PERMISSION_TABLE_PATH, "w"), indent=4)
            await update.message.reply_text(f"Permission {permission} revoked for {user_id}")
        else:
            await update.message.reply_text(f"Permission {permission} not found for {user_id}")

    @command_handler
    @restricted
    async def list_permissions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        permissions = "\n".join(
            [f"*{k}*: {', '.join([fr'{handler}' for handler in v])}" for k, v in PERMISSION_TABLE.items()])
        await update.message.reply_text(permissions)
