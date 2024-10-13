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

    def get_handlers(self, loaded_commands: list[str]) -> tuple[list[CommandHandler], dict]:
        handlers = []
        current_loaded_commands = []
        for command in self.info['commands']:
            command_name = command["command"]
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
                    current_loaded_commands.append(command_name)

        logger.info(
            f"Loaded plugin {self.info['name']}, commands: {current_loaded_commands}")
        return handlers, self.info
