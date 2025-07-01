import logging
import configparser
from datetime import datetime
import json

import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, CommandHandler, filters, ConversationHandler, MessageHandler, CallbackQueryHandler
import openai
from pydantic import BaseModel
# use google calendar
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth import exceptions

from tg_bot.core.handler import Handler
from tg_bot.core.auth import restricted_conversation

logger = logging.getLogger(__name__)

WAITING, ADDING, SELECTING = range(3)


class CalendarEvent(BaseModel):
    name: str
    place: str
    stime: str
    etime: str


TIMEZONE = "CET"

BASE_PROMPT = 'Extract the activity or event name, place, start time, end time in the format "{{"name":  "", "place": "", "stime": "", "etime": ""}}" from the following sentence: "{0}". The output should obey the following rules: 1. If any of the item is empty, use "None" to replace it. 2. name, "start time" and "end time" is mandatory. 3. "start time" and "end time" should be convert to UTC time zone with format "yyyy-mm-ddThh:mm:ssZ". Without further information, you should assume the time zone in the sentence is {3}. 4. Current time is {1} in {3} time zone, it\'s {2}. 5. By default, assume the end time is one hour later than the start time.'

WEEKDAY_DICT = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thurday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday"
}


class TimeArrangementHandler(Handler):
    @property
    def info(self):
        return {
            "name": "time_arrangement",
            "version": "1.0.0",
            "author": "thisiszy",
            "commands": [
                {
                    "command": "time_arrangement",
                    "description": "arrange time by text and voice, use /schedule to start, use /stopschedule to stop"
                },
                {
                    "command": "set_timezone",
                    "description": "set the timezone for the user, use /set\_timezone <timezone\> to set"
                }
            ],
            "message_type": ["text"]
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        config = configparser.ConfigParser()
        config.read(self.CONFIG_FOLDER / "config.ini")
        token = config['OPENAI']['API_KEY']
        self.client = openai.OpenAI(api_key=token)

        # If modifying these scopes, delete the file token.json.
        self.SCOPES = ['https://www.googleapis.com/auth/calendar']

        # Set up the SQLite database
        self.conn = sqlite3.connect(self.CONFIG_FOLDER / "storage.db")
        self.c = self.conn.cursor()
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS tokens
            (user_id INTEGER PRIMARY KEY, token TEXT, credentials TEXT)
        ''')

    def get_handlers(self, command_list) -> tuple[list[CommandHandler], dict]:
        if "set_timezone" in command_list or "schedule" in command_list:
            logger.error(
                logging.ERROR, f"Command 'set_timezone' or 'schedule' already exists, ignored!")
            return [], {}
        handlers = [ConversationHandler(
            entry_points=[CommandHandler("schedule", self.schedule)],
            states={
                WAITING: [MessageHandler(filters.TEXT & (~filters.COMMAND) | filters.VOICE, self.arrange_time_chatgpt)],
                SELECTING: [CallbackQueryHandler(self.selecting_calendar_callback)],
                ADDING: [CallbackQueryHandler(self.modify_calendar_callback)],
            },
            fallbacks=[CommandHandler("stopschedule", self.stopschedule)],
        ),
            CommandHandler("set_timezone", self.set_timezone)
        ]
        return handlers, self.info

    @restricted_conversation
    async def set_timezone(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        TIMEZONE = context.args[0]
        await update.message.reply_text(
            f"Timezone set to {TIMEZONE}"
        )

    @restricted_conversation
    async def schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "Send me text, I can arrange time for you.\n\n"
        )
        return WAITING

    async def stopschedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Cancels and ends the conversation."""
        await update.message.reply_text(
            "Canceled."
        )
        return ConversationHandler.END

    async def arrange_time_chatgpt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        prompt = None
        place_holder = None
        response = ""
        try:
            if update.message.text is not None:
                prompt = BASE_PROMPT.format(update.message.text, datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"), WEEKDAY_DICT[datetime.weekday(datetime.now())], TIMEZONE)
            if prompt is not None:
                logger.debug(f"Prompt: {prompt}")
                if place_holder is not None:
                    await context.bot.edit_message_text(
                        chat_id=place_holder.chat_id, message_id=place_holder.message_id, text="Parsing..."
                    )
                else:
                    place_holder = await context.bot.send_message(chat_id=update.effective_chat.id, text="Parsing...", reply_to_message_id=update.message.message_id)

                logger.info(f"Prompt: {prompt}")
                completion = completion = self.client.beta.chat.completions.parse(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": f"{prompt}"},
                    ],
                    response_format=CalendarEvent,
                )

                logger.info(f"Response: {completion}")
                keyboard = [[]]
                events_obj: list[CalendarEvent] = []
                events_text = [f"Time Zone: {TIMEZONE}"]
                for choice in completion.choices:
                    parsed_msg = choice.message.parsed
                    if parsed_msg is not None:
                        events_obj.append(parsed_msg)
                        events_text.append(
                            f"{choice.index}. {parsed_msg.model_dump()}")
                        keyboard[0].append(InlineKeyboardButton(
                            f"{choice.index}", callback_data=f"{choice.index}"))
                keyboard.append(
                    [InlineKeyboardButton("Cancel", callback_data="N")])
                # keyboard = [
                #     [
                #         InlineKeyboardButton("Apply", callback_data="Y"),
                #         InlineKeyboardButton("Cancel", callback_data="N"),
                #     ]
                # ]
                context.user_data["message"] = (
                    update.message.text, events_obj, place_holder)
                reply_markup = InlineKeyboardMarkup(keyboard)
                await context.bot.edit_message_text(
                    chat_id=place_holder.chat_id,
                    message_id=place_holder.message_id,
                    text="\n".join(events_text),
                )
                await context.bot.edit_message_reply_markup(
                    chat_id=place_holder.chat_id,
                    message_id=place_holder.message_id,
                    reply_markup=reply_markup
                )

                return SELECTING
        except Exception as e:
            logger.error(f"Error: {e}")
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error: {e}\nResponse: {response}\nExit conversation", reply_to_message_id=update.message.message_id)

            return ConversationHandler.END

    # input: selected event json
    # output: ask user to select calendar
    async def selecting_calendar_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        orig_text, events_obj, place_holder = context.user_data["message"]
        try:
            if update.callback_query.data != "N":
                calendar_serv = self.get_calendar_service(
                    update.effective_chat.id)
                calender_list = self.list_calendar(calendar_serv)

                keyboard = [[]]
                for idx, item in enumerate(calender_list):
                    keyboard[0].append(InlineKeyboardButton(
                        f"{item['summary']}", callback_data=f"{idx}"))
                keyboard.append(
                    [InlineKeyboardButton("Cancel", callback_data="N")])

                context.user_data["message"] = (orig_text, events_obj[int(
                    update.callback_query.data)], calender_list, place_holder.message_id)
                reply_markup = InlineKeyboardMarkup(keyboard)
                await context.bot.edit_message_reply_markup(
                    chat_id=place_holder.chat_id,
                    message_id=place_holder.message_id,
                    reply_markup=reply_markup
                )

                return ADDING
            else:
                await context.bot.edit_message_text(chat_id=update.effective_chat.id, text=f"Canceled\nschedule exit", message_id=place_holder.message_id)
                return ConversationHandler.END
        except Exception as e:
            logger.error(f"Error: {e}")
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error: {e}\nExit conversation", reply_to_message_id=update.message.message_id)
            return ConversationHandler.END

    # input: selected calendar
    # output: add event to calendar
    async def modify_calendar_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        orig_text, event_obj, calender_list, message_id = context.user_data["message"]
        try:
            if update.callback_query.data != "N":
                calendar_serv = self.get_calendar_service(
                    update.effective_chat.id)
                event_id = self.modify_calendar(orig_text, event_obj, calender_list[int(
                    update.callback_query.data)]['id'], calendar_serv)
                await context.bot.edit_message_text(chat_id=update.effective_chat.id, text=f"{event_id}", message_id=message_id)
                # await context.bot.edit_message_text(chat_id=update.effective_chat.id, text=f"Event added: {event}\nschedule exit", message_id=message_id)
            else:
                await context.bot.edit_message_text(chat_id=update.effective_chat.id, text=f"Canceled\nschedule exit", message_id=message_id)
        except Exception as e:
            logger.error(f"Error: {e}")
            await context.bot.edit_message_text(chat_id=update.effective_chat.id, text=f"Error: {e}, Event: {event_obj}\nschedule exit", message_id=message_id)
        finally:
            return ConversationHandler.END

    def update_token_crediential(self, user_id, secret, force_update=False):
        creds = None
        result = None
        # The database stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if not force_update:
            self.c.execute(
                'SELECT token, credentials FROM tokens WHERE user_id = ?', (user_id,))
            result = self.c.fetchone()
            secret = result[0]
            if result:
                creds = Credentials.from_authorized_user_info(
                    json.loads(result[1]), self.SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if secret is not None:
                    flow = InstalledAppFlow.from_client_config(
                        json.loads(secret), self.SCOPES)
                else:
                    if result:
                        secret = result[0]
                        if secret is not None:
                            flow = InstalledAppFlow.from_client_config(
                                json.loads(secret), self.SCOPES)
                        else:
                            logger.error("result[0] is None")
                            return None
                    else:
                        logger.error("No secret found")
                        return None
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            if secret is None:
                logger.error("No secret found, can't save")
                logger.error(creds.to_json())
                return None
            self.c.execute('INSERT OR REPLACE INTO tokens (user_id, token, credentials) VALUES (?, ?, ?)',
                           (user_id, secret, creds.to_json()))
            self.conn.commit()
        return creds

    def get_calendar_service(self, user_id):
        try:
            creds = self.update_token_crediential(user_id, None)
        except exceptions.RefreshError:
            self.c.execute(
                'SELECT token FROM tokens WHERE user_id = ?', (user_id,))
            result = self.c.fetchone()
            if result:
                creds = self.update_token_crediential(
                    user_id, result[0], force_update=True)
            else:
                raise exceptions.RefreshError

        service = build('calendar', 'v3', credentials=creds)

        return service

    def modify_calendar(self, orig_text, event: CalendarEvent, calender_id, service):
        try:
            event_dict = {
                'summary': event.name,
                'location': event.place,
                'description': orig_text,
                'start': {
                    'dateTime': event.stime,
                },
                'end': {
                    'dateTime': event.etime,
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 4 * 60},
                        {'method': 'popup', 'minutes': 40},
                    ],
                },
            }

            response = service.events().insert(
                calendarId=calender_id, body=event_dict).execute()
            return response.get('id')

        except HttpError as error:
            return f'An error occurred: {error}'

    def list_calendar(self, service):
        page_token = None
        calendar_list = []
        while True:
            cur_calendar_list = service.calendarList().list(pageToken=page_token).execute()
            for calendar_list_entry in cur_calendar_list['items']:
                calendar_list.append({
                    'summary': calendar_list_entry['summary'],
                    'id': calendar_list_entry['id']
                })
            page_token = cur_calendar_list.get('nextPageToken')
            if not page_token:
                break
        return calendar_list
