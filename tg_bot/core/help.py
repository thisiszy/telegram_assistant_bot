from telegram import Update
from telegram.ext import ContextTypes

from tg_bot.core.handler import Handler, command_handler


class Help(Handler):
    def __init__(self, help_infos: list[dict]):
        self.help_infos_raw = help_infos
        self.help_text: str = ""

        for help_info in self.help_infos_raw:
            clean_name = help_info['name'].replace("_", r"\_")
            clean_version = help_info['version'].replace(".", r"\.")
            self.help_text += f"*{clean_name}* \(v{clean_version}\): \n"
            for command in help_info['commands']:
                command_name, description = command["command"], command["description"]
                new_command_name = command_name.replace("_", r"\_")
                self.help_text += f"    _{new_command_name}_: {description}\n"

    @property
    def info(self):
        return {
            "name": "help",
            "version": "1.0.0",
            "author": "",
            "commands": [
                {"command": "help",
                    "description": r"Display help message"}
            ]
        }

    @command_handler
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=self.help_text, parse_mode="MarkdownV2")
