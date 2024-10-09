import importlib.resources

with importlib.resources.path('tg_bot', '__init__.py') as package_path:
    DEFAULT_PLUGIN_DIR = package_path.parent / "plugins"
    PACKAGE_PATH = package_path.parent
    DB_PATH = package_path.parent / "configs"/"storage.db"
