import sys
import os
import importlib
import logging
from telegram.ext import ApplicationBuilder, CommandHandler

def get_handlers(application: ApplicationBuilder, plugin_dir="plugins"):
    plugin_dir_full = os.path.join(os.path.dirname(__file__), plugin_dir)
    command_list = []
    help_info = []
    for base_folder in os.listdir(plugin_dir_full):
        base_folder_full = os.path.join(plugin_dir_full, base_folder)
        if os.path.isdir(base_folder_full):
            plugin_main = "__main__.py"
            if plugin_main in os.listdir(base_folder_full):
                # load plugin, one plugin may have multiple commands
                plugin_path = ".".join((plugin_dir, base_folder, plugin_main.replace('.py', '')))
                module = importlib.import_module(plugin_path)
                # add commands
                handlers, info = module.get_handlers(command_list)
                help_info.append(info['description'])
                for handler in handlers:
                    application.add_handler(handler)
    return help_info

if __name__ == "__main__":
    print(get_handlers())