# telegram_assistant_bot
A plugin based telegram bot. Use [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) as the bot backend.

# Quick start
## Install requirements
```bash
pip install -r requirements.txt
```

## Edit config file
```bash
touch config.ini
```
The config file should contain the following part.
```txt
[TELEGRAM]
ACCESS_TOKEN = <Telegram bot access token(required)>

[OPENAI]
API_KEY = <OpenAI key, refer to https://platform.openai.com/account/api-keys>

[CAPTION_GEN]
BASE_PATH = <Path to where you want to store the video files and caption files(required if use caption_gen)>
```

## Start the bot
```bash
python start.py
```

# Plugin framework
## Basic
Each function of the bot is written as a plugin. A simple plugin should be put into `plugins` folder and it must include a `__main__.py` file which is the plugin entry(without that, the plugin won't be detected and you can use this feature to disable a plugin). The file structure example is shown below:
```
- plugins
  - plugin1
    - __main__.py
    - a_txt_file.txt
  - plugin2 
    - __main__.py
  - plugin3 
    - __main__.py
```

## Write a plugin
A simple example of the plugin is(The same code is available in `plugins/heartbeat`):
```python
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
import logging

def get_info():
    return {
        "name": "alive", 
        "version": "1.0.0", 
        "author": "thisiszy",
        "description": "*alive*: Use /alive command to check if the bot is alive",
        "commands": ["alive"]
    }

# return handlers list and info. Currently the info must include "description" key 
# which is used to display help information when you send /help. The "description"
# should be in markdown format
def get_handlers(command_list):
    info = get_info()
    handlers = [CommandHandler("alive", alive)]
    if "alive" in command_list:
        logging.log(logging.ERROR, f"Command {command} already exists, ignored!")
        return []
    logging.log(logging.INFO, f"Loaded plugin alive, commands: alive")
    return handlers, info

async def alive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Alive!")
```
Each plugin must implement `get_handlers(command_list)` function.
