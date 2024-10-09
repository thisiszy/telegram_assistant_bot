from telegram import Update
from telegram.ext import ContextTypes

from tg_bot.core.handler import Handler

class Help(Handler):
    def __init__(self, help_info: str):
        self.help_info = help_info

    async def help_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=self.help_info, parse_mode="MarkdownV2")
