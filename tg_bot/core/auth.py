from functools import wraps
import json
import logging
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from tg_bot.core.handler import command_handler, Handler

logger = logging.getLogger(__name__)


class PermissionTable:
    d: dict[str, list[str]] = {}

    @classmethod
    def __contains__(cls, user_id: str) -> bool:
        assert isinstance(user_id, str), "User ID must be a string"
        return user_id in cls.d

    @classmethod
    def __getitem__(cls, user_id: str) -> list[str]:
        assert isinstance(user_id, str), "User ID must be a string"
        return cls.d.get(user_id, [])

    @classmethod
    def __setitem__(cls, user_id: str, permissions: list[str]) -> None:
        assert isinstance(user_id, str), "User ID must be a string"
        assert isinstance(permissions, list), "Permissions must be a list"
        cls.d[user_id] = permissions

    @classmethod
    def items(cls):
        return cls.d.items()

    @classmethod
    def load(cls, path: Path):
        if path.exists():
            logger.info(f"Loading permission table from {path}")
            with open(path, "r") as f:
                cls.d = json.load(f)
        else:
            logger.warning(
                f"Permission table file {path} does not exist, initializing empty table"
            )
            cls.d = {}

    @classmethod
    def save(cls, path: Path):
        with open(path, "w") as f:
            json.dump(cls.d, f, indent=4)
        logger.info(f"Permission table saved to {path}")


permission_table = PermissionTable()


def restricted(func):
    @wraps(func)
    async def wrapped(cls, update, context, *args, **kwargs):
        user_id = str(update.effective_user.id)
        if user_id in permission_table and func.__name__ in permission_table[user_id]:
            return await func(cls, update, context, *args, **kwargs)
        else:
            logger.error(
                f"[Unauthorized access] {user_id} tried to access {func.__name__}"
            )
            return await update.message.reply_text("Unauthorized access denied")

    return wrapped


def restricted_conversation(func):
    @wraps(func)
    async def wrapped(cls, update, context, *args, **kwargs):
        user_id = str(update.effective_user.id)
        if user_id in permission_table and func.__name__ in permission_table[user_id]:
            return await func(cls, update, context, *args, **kwargs)
        else:
            logger.error(
                f"[Unauthorized access] {user_id} tried to access {func.__name__}"
            )
            await update.message.reply_text("Unauthorized access denied")
            return ConversationHandler.END

    return wrapped


class Auth(Handler):
    def __init__(self, config_dir: Path):
        super().__init__(config_dir)
        self.permission_table_path = self.CONFIG_FOLDER / "permissions.json"
        permission_table.load(self.permission_table_path)

    @property
    def info(self):
        return {
            "name": "auth",
            "description": "Authentication and authorization",
            "commands": [
                {
                    "command": "add_permission",
                    "description": "Add a permission to a user",
                },
                {
                    "command": "revoke_permission",
                    "description": "Revoke a permission from a user",
                },
                {"command": "list_permissions", "description": "List all permissions"},
            ],
        }

    @command_handler
    @restricted
    async def add_permission(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) != 2:
            await update.message.reply_text(
                r"Usage: /add_permission <permission> <user_id>"
            )
            return
        user_id = context.args[0]
        permission = context.args[1]
        if user_id not in permission_table:
            permission_table[user_id] = []
        if permission in permission_table[user_id]:
            await update.message.reply_text(
                f"Permission {permission} already added for {user_id}"
            )
        else:
            permission_table[user_id].append(permission)
            logger.debug(f"New permission table: {permission_table}")
            logger.info(f"Permission {permission} added for {user_id}")
            permission_table.save(self.permission_table_path)
            await update.message.reply_text(
                f"Permission {permission} added for {user_id}"
            )

    @command_handler
    @restricted
    async def revoke_permission(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        if len(context.args) != 2:
            await update.message.reply_text(
                r"Usage: /revoke_permission <permission> <user_id>"
            )
            return
        user_id = context.args[0]
        permission = context.args[1]
        if user_id not in permission_table:
            await update.message.reply_text(f"User {user_id} not found")
        elif permission in permission_table[user_id]:
            permission_table[user_id].remove(permission)
            logger.debug(f"New permission table: {permission_table}")
            logger.info(f"Permission {permission} revoked for {user_id}")
            permission_table.save(self.permission_table_path)
            await update.message.reply_text(
                f"Permission {permission} revoked for {user_id}"
            )
        else:
            await update.message.reply_text(
                f"Permission {permission} not found for {user_id}"
            )

    @command_handler
    @restricted
    async def list_permissions(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        permissions = "\n".join(
            [
                f"*{k}*: {', '.join([fr'{handler}'.replace('_', r'\_') for handler in v])}"
                for k, v in permission_table.items()
            ]
        )
        await update.message.reply_text(permissions, parse_mode="MarkdownV2")
