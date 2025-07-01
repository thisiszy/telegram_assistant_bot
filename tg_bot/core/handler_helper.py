import importlib
from pathlib import Path
import ast
import logging

from telegram.ext import CommandHandler, Application
from telegram.ext import ApplicationBuilder

from tg_bot.utils.consts import DEFAULT_PLUGIN_DIR, PACKAGE_PATH
from tg_bot.core.handler import Handler
from tg_bot.core.help import Help
from tg_bot.core.auth import Auth

logger = logging.getLogger(__name__)


def load_plugins(application: ApplicationBuilder, config_dir: Path, plugin_dir: Path = DEFAULT_PLUGIN_DIR) -> list[dict]:
    loaded_commands = []
    help_msgs = []
    for base_folder in plugin_dir.iterdir():
        plugin_main = base_folder / "__main__.py"
        if base_folder.is_dir() and plugin_main.exists():
            # load plugin, one plugin may have multiple commands
            with open(plugin_main, "r") as f:
                file_contents = f.read()
            try:
                tree = ast.parse(file_contents)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        for base in node.bases:
                            if isinstance(base, ast.Name) and base.id == "Handler":
                                plugin_path = plugin_main.relative_to(
                                    PACKAGE_PATH.parent).as_posix().replace('/', '.').replace('.py', '')
                                module = importlib.import_module(plugin_path)
                                # add commands
                                try:
                                    plugin: type[Handler] | None = getattr(
                                        module, node.name, None
                                    )(config_dir)
                                    handlers, msg = plugin.get_handlers(
                                        loaded_commands)
                                    help_msgs.append(msg)
                                    for handler in handlers:
                                        application.add_handler(handler)
                                except Exception as e:
                                    logger.error(f"Error loading plugin {plugin_main}: {e}")
            except SyntaxError:
                logger.error(f"Error parsing {plugin_main}. Skipping...")
    return help_msgs


def add_handlers(application: Application, config_dir: Path):
    help_msg = load_plugins(application, config_dir = config_dir)
    help = Help(help_msg)
    echo_handler = CommandHandler("help", help.help)
    application.add_handler(echo_handler)

    auth = Auth(config_dir)
    add_permission_handler = CommandHandler("add_permission", auth.add_permission)
    application.add_handler(add_permission_handler)
    revoke_permission_handler = CommandHandler("revoke_permission", auth.revoke_permission)
    application.add_handler(revoke_permission_handler)
    list_permissions_handler = CommandHandler("list_permissions", auth.list_permissions)
    application.add_handler(list_permissions_handler)


if __name__ == "__main__":
    print(load_plugins())
