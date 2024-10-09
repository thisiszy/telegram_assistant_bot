from telegram import Update
from telegram.ext import ContextTypes

from tg_bot.core.handler import Handler, command_handler


class Heartbeat(Handler):
    @property
    def info(self):
        return {
            "name": "alive",
            "version": "1.0.0",
            "author": "thisiszy",
            "commands": [
                {
                    "command": "alive",
                    "description": r"Use /alive command to check if the bot is alive"
                }
            ]
        }

    @command_handler
    async def alive(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Alive!")
