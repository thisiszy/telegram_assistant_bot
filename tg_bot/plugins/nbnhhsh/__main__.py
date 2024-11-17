import logging
import requests

from telegram import Update
from telegram.ext import ContextTypes

from tg_bot.core.handler import Handler, command_handler

logger = logging.getLogger(__name__)


class NbnhhshQuery(Handler):
    def __init__(self):
        super().__init__()

    @property
    def info(self):
        return {
            "name": "nbnhhsh query",
            "version": "1.0.0",
            "author": "thisiszy",
            "commands": [
                {
                    "command": "hhsh",
                    "description": r"社交平台上通过拼音首字母缩写指代特定词句的情况越来越多，为了让更多人能勉强理解这一门另类沟通方式、做了这一个划词转义工具。usage: /hhsh <text\>",
                }
            ]
        }

    @command_handler
    async def hhsh(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) != 1:
            await update.message.reply_text(self.info["commands"][0]["description"])
            return

        text = context.args[0].lower()
        logger.info(f"hhsh query: {text}")

        try:
            response = requests.post(
                "https://lab.magiconch.com/api/nbnhhsh/guess",
                json={"text": text}
            )
            logger.debug(f"hhsh response: {response.json()}")

            if response.status_code == 200:
                data = response.json()
                if not data:
                    logger.info(f"hhsh response is empty")
                    await update.message.reply_text(f"未找到 '{text}' 的解释")
                    return

                result = data[0]
                if "trans" not in result or not result["trans"]:
                    logger.info(f"hhsh response trans is empty")
                    await update.message.reply_text(f"未找到 '{text}' 的解释")
                    return

                translations = "\n".join(
                    [f"• {trans}" for trans in result["trans"]])
                logger.info(f"hhsh response translations: {translations}")
                await update.message.reply_text(
                    f"'{text}' 可能的含义：\n{translations}"
                )
            else:
                logger.info(f"hhsh response status code: {response.status_code}")
                await update.message.reply_text("查询失败，请稍后重试")

        except Exception as e:
            logger.error(f"Error in nbnhhsh query: {str(e)}")
            await update.message.reply_text("查询时发生错误，请稍后重试")
