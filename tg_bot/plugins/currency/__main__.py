import logging
import re

import requests
import sqlite3

from telegram import Update
from telegram.ext import ContextTypes

from tg_bot.core.handler import Handler, command_handler
from tg_bot.utils.consts import DB_PATH


class CurrencyQuery(Handler):
    def __init__(self):
        super().__init__()
        # Set up the SQLite database
        self.conn = sqlite3.connect(DB_PATH)
        self.c = self.conn.cursor()
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS currency
            (user_id INTEGER PRIMARY KEY, base_currency TEXT)
        ''')

    @property
    def info(self):
        return {
            "name": "currency query",
            "version": "1.0.0",
            "author": "thisiszy",
            "commands": [
                {
                    "command": "convert_currency",
                    "description": r"Query currency rate, usage: /convert\_currency <source\_currency\> <target\_currency\>",
                },
                {
                    "command": "trans",
                    "description": r"Convert currency, usage: /trans",
                },
                {
                    "command": "set_currency",
                    "description": r"Set the base currency, usage: /set\_currency <currency\>",
                },
                {
                    "command": "get_currency",
                    "description": r"Get the base currency, usage: /get\_currency",
                }
            ]
        }

    @command_handler
    async def set_currency(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) != 1:
            await update.message.reply_text("Please specify the base currency you want to set.")
            return
        base_currency = context.args[0].upper()
        self.c.execute('INSERT OR REPLACE INTO currency (user_id, base_currency) VALUES (?, ?)',
                  (update.message.from_user.id, base_currency))
        self.conn.commit()
        await update.message.reply_text(f"Base currency set to {base_currency}")

    @command_handler
    async def get_currency(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.c.execute('SELECT base_currency FROM currency WHERE user_id = ?', (update.message.from_user.id,))
        base_currency = self.c.fetchone()
        if base_currency is None:
            await update.message.reply_text("Please set the base currency first.")
            return
        base_currency = base_currency[0]
        await update.message.reply_text(f"Base currency is {base_currency}")

    @command_handler
    async def convert_currency(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) != 2:
            await update.message.reply_text(self.info["commands"][0]["description"])
            return
        source = context.args[0].upper()
        target = context.args[1].upper()
        response = requests.get(
            f"https://hexarate.paikama.co/api/rates/latest/{source}?target={target}")
        if response.status_code == 200:
            data = response.json()["data"]
            await update.message.reply_text(f"1 USD = {data['mid']} GBP")
        else:
            await update.message.reply_text("Failed to fetch currency rates")

    @command_handler
    async def trans(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # this message replies to another message, find the number in the message and convert it to CNY
        message = update.message.reply_to_message
        if message is None or not message.text:
            await update.message.reply_text("Please reply to a message containing the amount you want to convert.")
            return

        src_user_id = message.from_user.id
        self.c.execute('SELECT base_currency FROM currency WHERE user_id = ?', (src_user_id,))
        source = self.c.fetchone()
        if source is None:
            await update.message.reply_text("Please set the base currency first.")
            return
        source = source[0]

        target_user_id = update.message.from_user.id
        self.c.execute('SELECT base_currency FROM currency WHERE user_id = ?', (target_user_id,))
        target = self.c.fetchone()
        if target is None:
            await update.message.reply_text("Please set the target currency first.")
            return
        target = target[0]

        # use re to find all the number in the message
        numbers = re.findall(r'\d+', message.text)
        if len(numbers) == 0:
            await update.message.reply_text("Please reply to a message containing the amount you want to convert.")
            return
        # convert the amount to CNY
        response = requests.get(
            f"https://hexarate.paikama.co/api/rates/latest/{source}?target={target}")
        if response.status_code == 200:
            data = response.json()["data"]
            reply_msg = ""
            for number in numbers:
                cny = data["mid"] * float(number)
                reply_msg += f"{number} {source} = {cny:.2f} {target}\n"
            await update.message.reply_text(reply_msg)
        else:
            await update.message.reply_text("Failed to fetch currency rates")
