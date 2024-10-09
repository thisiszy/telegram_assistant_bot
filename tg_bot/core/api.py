import importlib
from pathlib import Path
import ast
import logging

from telegram.ext import ApplicationBuilder
from tg_bot.utils.consts import DEFAULT_PLUGIN_DIR, PACKAGE_PATH
from tg_bot.core.handler import Handler

logger = logging.getLogger(__name__)


def get_handlers(application: ApplicationBuilder, plugin_dir: Path = DEFAULT_PLUGIN_DIR):
    loaded_commands = []
    help_info = []
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
                                plugin: type[Handler] | None = getattr(
                                    module, node.name, None
                                )()
                                handlers = plugin.get_handlers(
                                    loaded_commands)
                                info = plugin.info
                                help_info.append(info['description'])
                                for handler in handlers:
                                    application.add_handler(handler)
            except SyntaxError:
                logger.error(f"Error parsing {plugin_main}. Skipping...")
    return help_info


if __name__ == "__main__":
    print(get_handlers())
