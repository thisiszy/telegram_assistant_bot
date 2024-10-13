# telegram_assistant_bot

A plugin based telegram bot. Use [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) as the bot backend.

# Quick start

## Install requirements

```bash
pip install -e .
```

## Edit config file

```bash
touch tg_bot/configs/config.ini
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
python tg-assistant-start
```

# Plugin framework

## Basic

Each function of the bot is written as a plugin. A simple plugin should be put into `plugins` folder and it must include a `__main__.py` file which is the plugin entry(without that, the plugin won't be detected and you can use this feature to disable a plugin). The file structure example is shown below:

```
- tg_bot/plugins
  - plugin1
    - __main__.py
    - a_txt_file.txt
  - plugin2
    - __main__.py
  - plugin3
    - __main__.py
```

## Write a plugin

A simple example of the plugin is(The same code is available in `tg_bot/plugins/heartbeat`):

```python
from tg_bot.core.handler import Handler, command_handler


class Heartbeat(Handler):
    @property
    def info(self):
        return {
            "name": "alive",
            "version": "1.0.0",
            "author": "thisiszy",
            "commands": [
                {
                    "command": "alive",
                    "description": r"Use /alive command to check if the bot is alive"
                }
            ]
        }

    @command_handler
    async def alive(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Alive!")
```

Each plugin must implement `info` function.
