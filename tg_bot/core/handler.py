import logging
from telegram.ext import CommandHandler

logger = logging.getLogger(__name__)


def command_handler(func):
    setattr(func, "command_handler", True)
    return func


class Handler:
    def __init__(self):
        pass

    @property
    def info(self):
        return {
            "name": "handler",
            "version": "1.0.0",
            "author": "",
            "description": "base_handler",
            "commands": []
        }

    def get_handlers(self, loaded_commands: list[str]) -> tuple[list[CommandHandler], str]:
        help_msg = f"*{self.info['name']}*: \n"
        handlers = []
        loaded_commands = []
        for command in self.info['commands']:
            command_name, description = command["command"], command["description"]
            if command_name in loaded_commands:
                logger.error(
                    logging.ERROR, f"Command {command_name} already exists, ignored!")
                continue
            # Find the method with the command_handler decorator
            if command_name in dir(self):
                attr = getattr(self, command_name)
                if callable(attr) and getattr(attr, "command_handler", False) is True:
                    handlers.append(CommandHandler(command_name, attr))
                    loaded_commands.append(command_name)
                    new_command_name = command_name.replace("_", r"\_")
                    help_msg += f"    _{new_command_name}_: {description}\n"

        logger.info(
            f"Loaded plugin {self.info['name']}, commands: {loaded_commands}")
        return handlers, help_msg