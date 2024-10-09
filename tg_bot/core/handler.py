import logging
from telegram.ext import CommandHandler

logger = logging.getLogger(__name__)


def command_handler():
    def decorator(func):
        setattr(func, "command_handler", True)
        return func

    return decorator


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

    def get_handlers(self, loaded_commands: list[str]) -> list[CommandHandler]:
        info = self.info
        handlers = []
        loaded_commands = []
        for command in info['commands']:
            if command in loaded_commands:
                logger.error(
                    logging.ERROR, f"Command {command} already exists, ignored!")
                continue
            # Find the method with the command_handler decorator
            if command in dir(self):
                attr = getattr(self, command)
                if callable(attr) and getattr(attr, "command_handler", False) is True:
                    handlers.append(CommandHandler(command, attr))
                    loaded_commands.append(command)

        logger.info(
            f"Loaded plugin {info['name']}, commands: {loaded_commands}")
        return handlers
