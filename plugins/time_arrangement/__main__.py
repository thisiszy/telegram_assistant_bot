from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, CommandHandler, filters, ConversationHandler, MessageHandler, CallbackQueryHandler
import logging
import configparser
from datetime import datetime
import json
from datetime import datetime
from tzlocal import get_localzone
import re
# import openai GPT-3 token
import openai
config = configparser.ConfigParser()
config.read('config.ini')
token = config['OPENAI']['ACCESS_TOKEN_GPT3']
openai.api_key = token

# import whisper
import whisper
import shutil
import os
model = whisper.load_model("small", download_root="env/share/whisper")
AUDIO_FILE_PATH = "env/share/whisper/audio"

if os.path.exists(AUDIO_FILE_PATH):
    shutil.rmtree(AUDIO_FILE_PATH)
os.makedirs(AUDIO_FILE_PATH)

# use reverse chatgpt
from revChatGPT.V1 import Chatbot

# use google calendar
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']

chatbot = Chatbot(config={
  "access_token": config['OPENAI']['ACCESS_TOKEN_CHATGPT']
})

def get_info():
    return {
        "name": "time_arrangement", 
        "version": "1.0.0", 
        "author": "thisiszy",
        "description": "*time\_arrange*: arrange time by text and voice, use /schedule to start, use /stopschedule to stop",
        "commands": [""],
        "message_type": ["text", "audio"]
    }

WAITING, ADDING = range(2)

def get_handlers(command_list):
    info = get_info()
    handlers = [ConversationHandler(
        entry_points=[CommandHandler("schedule", start)],
        states={
            WAITING: [MessageHandler(filters.TEXT & (~filters.COMMAND) | filters.VOICE, arrange_time_chatgpt)],
            ADDING: [CallbackQueryHandler(modify_calender_callback)],
        },
        fallbacks=[CommandHandler("stopschedule", cancel)],
    )]
    logging.log(logging.INFO, f"Loaded plugin {info['name']}, commands: {info['commands']}, message_type: {info['message_type']}")
    return handlers, info

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Now you can send me the text message, and I will answer your question.\n\n"
    )
    return WAITING

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    await update.message.reply_text(
        "Bye! Looking forward to chat with you next time."
    )
    return ConversationHandler.END

async def arrange_time_gpt3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = None
    place_holder = None
    try:
        if update.message.text is not None:
            prompt = update.message.text
        if update.message.voice is not None:
            place_holder = await context.bot.send_message(chat_id=update.effective_chat.id, text="Converting...", reply_to_message_id=update.message.message_id)
            file = await update.message.voice.get_file()
            audio_file_path = os.path.join(AUDIO_FILE_PATH, file.file_id)
            await file.download_to_drive(audio_file_path)
            result = model.transcribe(audio_file_path)
            logging.log(logging.INFO, f"Received audio file: {audio_file_path}")
            logging.log(logging.INFO, f"Recognized text: {result['text']}")
            prompt = result["text"]
        if prompt is not None:
            if place_holder is not None:
                await context.bot.edit_message_text(
                    chat_id=place_holder.chat_id, message_id=place_holder.message_id, text="Thinking..."
                )
            else:
                place_holder = await context.bot.send_message(chat_id=update.effective_chat.id, text="Thinking...", reply_to_message_id=update.message.message_id)
            gpt_model = "text-davinci-003"
            temperature = 0.5
            max_tokens = 4000

            # Generate a response
            response = openai.Completion.create(
                engine=gpt_model,
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )
            await context.bot.edit_message_text(
                chat_id=place_holder.chat_id, message_id=place_holder.message_id, text=response.choices[0].text.strip()
            )
            # await context.bot.send_message(chat_id=update.effective_chat.id, text=response.choices[0].text.strip())
            return ADDING
    except Exception as e:
        logging.log(logging.ERROR, f"Error: {e}")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Error {e}", reply_to_message_id=update.message.message_id)
        return WAITING


BASE_PROMPT = 'Extract the activity name, place, start time, end time in the format "{{"name":  "", "place": "", "stime": "", "etime": ""}}" from the following sentence: "{0}". The output should obey the following rules: 1. If any of the item is empty, use "None" to replace it. 2. name, start time and end time is mandatory. 3. start time and end time should be represented by "yyyy-mm-dd hh:mm:ss" in 24-hour clock format. Current time is {1}. 4. If there is no end time extracted, you can assume the end time is one hour later than the start time. 5. Your response should only contain the extracted information in that format and do not contain "Explanation", "Note" or something else.'

async def arrange_time_chatgpt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = None
    place_holder = None
    response = ""
    try:
        if update.message.text is not None:
            prompt = BASE_PROMPT.format(update.message.text, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        if update.message.voice is not None:
            place_holder = await context.bot.send_message(chat_id=update.effective_chat.id, text="Converting...", reply_to_message_id=update.message.message_id)
            file = await update.message.voice.get_file()
            audio_file_path = os.path.join(AUDIO_FILE_PATH, file.file_id)
            await file.download_to_drive(audio_file_path)
            result = model.transcribe(audio_file_path)
            logging.debug(f"Received audio file: {audio_file_path}")
            logging.debug(f"Recognized text: {result['text']}")
            prompt = BASE_PROMPT.format(result["text"], datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        if prompt is not None:
            # logging.debug(f"Prompt: {prompt}")
            # if place_holder is not None:
            #     await context.bot.edit_message_text(
            #         chat_id=place_holder.chat_id, message_id=place_holder.message_id, text="Thinking..."
            #     )
            # else:
            #     place_holder = await context.bot.send_message(chat_id=update.effective_chat.id, text="Thinking...", reply_to_message_id=update.message.message_id)

            # for data in chatbot.ask(prompt):
            #     response = data["message"]
            # logging.info(f"Response: {response}")
            place_holder = await context.bot.send_message(chat_id=update.effective_chat.id, text="Thinking...", reply_to_message_id=update.message.message_id)
            response = '{"name": "Career Counseling with Goldwyn", "place": "Online", "stime": "2023-02-24 09:00:00", "etime": "2023-02-24 16:00:00"}'
            pattern = re.compile(r'{"name":.*, "place":.*, "stime":.*, "etime":.*}', flags=0)
            matched = pattern.findall(response)
            if len(matched) > 0:
                keyboard = [
                    [
                        InlineKeyboardButton("Apply", callback_data="Y"),
                        InlineKeyboardButton("Restart", callback_data="N"),
                    ]
                ]
                context.user_data["message"] = (update.message.text, response)
                reply_markup = InlineKeyboardMarkup(keyboard)
                await context.bot.edit_message_text(
                    chat_id=place_holder.chat_id,
                    message_id=place_holder.message_id,
                    text=matched[0],
                )
                await context.bot.edit_message_reply_markup(
                    chat_id=place_holder.chat_id,
                    message_id=place_holder.message_id,
                    reply_markup=reply_markup
                )
                return ADDING
            else:
                await context.bot.edit_message_text(
                    chat_id=place_holder.chat_id, message_id=place_holder.message_id, text=f"Not matched: {response}"
                )
                return WAITING
    except Exception as e:
        logging.log(logging.ERROR, f"Error: {e}")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error: {e}, Response: {response}", reply_to_message_id=update.message.message_id)

        return WAITING

async def modify_calender_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    orig_text, event = context.user_data["message"]
    try:
        if update.callback_query.data == "Y":
            modify_calender(orig_text, json.loads(event))
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Event added: {event}\nschedule exit", reply_to_message_id=update.callback_query.message.message_id)
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Canceled\nschedule exit", reply_to_message_id=update.callback_query.message.message_id)
    except Exception as e:
        logging.log(logging.ERROR, f"Error: {e}")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error: {e}, Event: {event}\nschedule exit", reply_to_message_id=update.callback_query.message.message_id)
    finally:
        return ConversationHandler.END

def check_crediential():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

def modify_calender(orig_text, event):
    creds = check_crediential()

    try:
        # get the local time zone
        timezone = datetime.now().astimezone().tzinfo
        timezone_str = str(get_localzone())

        # get the current UTC offset for the local time zone
        utc_offset = timezone.utcoffset(datetime.now()).total_seconds() / 3600

        # format the offset as a string
        offset_str = "{:+03d}:00".format(int(utc_offset))
        # format the datetime object as a string in the desired format
        def format_datetime(time : str) -> str:
            dt = datetime.strptime(time, "%Y-%m-%d %H:%M:%S")
            return dt.strftime("%Y-%m-%dT%H:%M:%S") + offset_str

        service = build('calendar', 'v3', credentials=creds)
        event = {
            'summary': event['name'],
            'location': event['place'],
            'description': orig_text,
            'start': {
                'dateTime': format_datetime(event["stime"]),
                'timeZone': timezone_str,
            },
            'end': {
                'dateTime': format_datetime(event["etime"]),
                'timeZone': timezone_str,
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 4 * 60},
                    {'method': 'popup', 'minutes': 40},
                ],
            },
        }

        event = service.events().insert(calendarId='primary', body=event).execute()
        return event.get('htmlLink')


    except HttpError as error:
        return f'An error occurred: {error}'
