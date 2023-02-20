from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, filters, ConversationHandler, MessageHandler
import logging
import configparser

# use reverse chatgpt
from revChatGPT.V1 import Chatbot


config = configparser.ConfigParser()
config.read('config.ini')
chatbot = Chatbot(config={
  "access_token": config['OPENAI']['ACCESS_TOKEN_CHATGPT']
})

# Set up the SQLite database
import sqlite3
conn = sqlite3.connect('storage.db')
c = conn.cursor()
c.execute('''
    CREATE TABLE IF NOT EXISTS chats
    (user_id INTEGER PRIMARY KEY, conversation_id TEXT)
''')
c.execute('''
    DELETE FROM chats
''')
conn.commit()

def get_info():
    return {
        "name": "chatgpt_conversation", 
        "version": "1.0.0", 
        "author": "thisiszy",
        "description": "*chatgpt\_conversation*: chat with chatgpt, /chat to start, /stopchat to stop",
        "commands": [""],
        "message_type": ["text"]
    }

CHATTING = 1

def get_handlers(command_list):
    info = get_info()
    handlers = [ConversationHandler(
        entry_points=[CommandHandler("chat", start)],
        states={
            CHATTING: [MessageHandler(filters.TEXT & (~filters.COMMAND), chat_with_chatgpt)],
        },
        fallbacks=[CommandHandler("stopchat", cancel)],
    )]
    logging.log(logging.INFO, f"Loaded plugin {info['name']}, commands: {info['commands']}, message_type: {info['message_type']}")
    command_list.append("chat")
    command_list.append("stopchat")
    return handlers, info

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Now let's chat!\n\n"
    )
    return CHATTING

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    user_id = update.effective_user.id
    c.execute('SELECT conversation_id from chats WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    if result is not None:
        conv_id = result[0]
        chatbot.delete_conversation(conv_id)
        c.execute('DELETE from chats WHERE user_id = ?', (user_id,))
        conn.commit()
    await update.message.reply_text(
        "Bye! See you next time."
    )
    return ConversationHandler.END

async def chat_with_chatgpt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        prompt = update.message.text
    except AttributeError as e:
        return CHATTING
    try:
        if prompt is not None:
            user_id = update.effective_user.id
            c.execute('SELECT conversation_id FROM chats WHERE user_id = ?', (user_id,))
            result = c.fetchone()
            conv_id = None
            if result is not None:
                conv_id = result[0]
            logging.debug(f"Prompt: {prompt}")
            place_holder = await context.bot.send_message(chat_id=update.effective_chat.id, text="Thinking...", reply_to_message_id=update.message.message_id)

            for data in chatbot.ask(prompt, conversation_id=conv_id):
                response = data["message"]
            logging.debug(f"Response: {response}")
            logging.info(f"Conversation ID: {chatbot.conversation_id}")
            if conv_id is None:
                conv_id = chatbot.conversation_id
                chatbot.change_title(conv_id, str(user_id))
                c.execute('INSERT INTO chats VALUES (?, ?)', (user_id, conv_id))
                conn.commit()
            await context.bot.edit_message_text(
                chat_id=place_holder.chat_id,
                message_id=place_holder.message_id,
                text=response,
            )
            return CHATTING
    except Exception as e:
        logging.log(logging.ERROR, f"Error: {e}")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error: {e}\nChat end!", reply_to_message_id=update.message.message_id)

        return ConversationHandler.END
