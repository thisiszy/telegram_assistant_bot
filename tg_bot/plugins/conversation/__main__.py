import logging
import configparser

import aisuite as ai
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, filters, ConversationHandler, MessageHandler

from tg_bot.core.handler import Handler
from tg_bot.core.auth import restricted_conversation

logger = logging.getLogger(__name__)
CHATTING = 1


class LLMConversationHandler(Handler):
    @property
    def info(self):
        return {
            "name": "conversation",
            "version": "1.0.0",
            "author": "thisiszy",
            "commands": [
                {
                    "command": "chat",
                    "description": "chat with chatgpt, use /chat to start, use /stopchat to stop"
                },
                {
                    "command": "stopchat",
                    "description": "stop chat with chatgpt, use /stopchat to stop"
                }
            ],
            "message_type": ["text"]
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        config = configparser.ConfigParser()
        config.read(self.CONFIG_FOLDER / "config.ini")
        self.MODEL = "openai:gpt-4o-mini"
        PROVIDOR_CONFIGS = {
            "openai": {"api_key": config['OPENAI']['API_KEY']},
        }
        self.client = ai.Client(PROVIDOR_CONFIGS)
        self.conversations: dict[int, list[dict[str, str]]] = {}

    def get_handlers(self, command_list):
        if "chat" in command_list or "stopchat" in command_list:
            logger.error(
                f"Command 'chat' or 'stopchat' already exists, ignored!")
            return [], {}
        handlers = [ConversationHandler(
            entry_points=[CommandHandler("chat", self.chat)],
            states={
                CHATTING: [MessageHandler(filters.TEXT & (~filters.COMMAND), self.chat_with_llm)],
            },
            fallbacks=[CommandHandler("stopchat", self.stopchat)],
        )]
        return handlers, self.info

    @restricted_conversation
    async def chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "Now let's chat!\n\n"
        )
        return CHATTING

    @restricted_conversation
    async def stopchat(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancels and ends the conversation."""
        user_id = update.effective_user.id
        if user_id in self.conversations:
            self.conversations.pop(user_id)
        await update.message.reply_text(
            "Bye! See you next time."
        )
        return ConversationHandler.END

    async def chat_with_llm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            user_prompt = update.message.text
        except AttributeError as e:
            return CHATTING
        if user_prompt is not None:
            user_id = update.effective_user.id
            logger.debug(f"Prompt: {user_prompt}")
            place_holder = await context.bot.send_message(chat_id=update.effective_chat.id, text="Thinking...", reply_to_message_id=update.message.message_id)
            messages = self.conversations.get(user_id, [])
            messages.append({"role": "user", "content": f"{user_prompt}"})
            try:
                response = self.client.chat.completions.create(
                    model=self.MODEL,
                    messages=messages,
                )
                # print(response.choices[0].message.content)
                logger.info(f"Available choices: {len(response.choices)}")
                for idx, choice in enumerate(response.choices):
                    logger.info(f"{idx}: {choice.message.content}")
                if len(response.choices) > 0:
                    message = response.choices[0].message.content
                else:
                    message = "No response from LLM"
                await context.bot.edit_message_text(
                    chat_id=place_holder.chat_id,
                    message_id=place_holder.message_id,
                    text=message,
                )
                messages.append({"role": "assistant", "content": message})
                self.conversations[user_id] = messages
                return CHATTING
            except Exception as e:
                logger.error(f"Error: {e}")
                await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error: {e}\nChat end!", reply_to_message_id=update.message.message_id)
                self.conversations.pop(user_id)

            return ConversationHandler.END
        else:
            return CHATTING
