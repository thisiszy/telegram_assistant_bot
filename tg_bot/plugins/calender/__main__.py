from telegram import Update
from telegram.ext import ContextTypes
import logging

# use google calendar
import datetime
import json

import sqlite3
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth import exceptions

from tg_bot.core.handler import Handler, command_handler
from tg_bot.core.auth import restricted
from tg_bot.utils.consts import DB_PATH

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Set up the SQLite database
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute('''
    CREATE TABLE IF NOT EXISTS tokens
    (user_id INTEGER PRIMARY KEY, token TEXT, credentials TEXT)
''')


def update_token_crediential(user_id, secret, force_update=False):
    creds = None
    result = None
    # The database stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if not force_update:
        c.execute(
            'SELECT token, credentials FROM tokens WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        secret = result[0]
        if result:
            creds = Credentials.from_authorized_user_info(
                json.loads(result[1]), SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if secret is not None:
                breakpoint()
                flow = InstalledAppFlow.from_client_config(
                    json.loads(secret), SCOPES)
            else:
                if result:
                    secret = result[0]
                    if secret is not None:
                        flow = InstalledAppFlow.from_client_config(
                            json.loads(secret), SCOPES)
                    else:
                        logging.error("result[0] is None")
                        return None
                else:
                    logging.error("No secret found")
                    return None
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        if secret is None:
            logging.error("No secret found, can't save")
            logging.error(creds.to_json())
            return None
        c.execute('INSERT OR REPLACE INTO tokens (user_id, token, credentials) VALUES (?, ?, ?)',
                  (user_id, secret, creds.to_json()))
        conn.commit()
    return creds


def list_calendar(service):
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


def list_events(user_id):
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    try:
        creds = update_token_crediential(user_id, None)
    except exceptions.RefreshError:
        c.execute('SELECT token FROM tokens WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        if result:
            creds = update_token_crediential(
                user_id, result[0], force_update=True)
        else:
            raise exceptions.RefreshError
    if creds is None:
        return "Please authorize the bot to access your Google Calendar by /auth <secret token>"

    try:
        service = build('calendar', 'v3', credentials=creds)

        # Call the Calendar API
        time_now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        time_max = (datetime.datetime.utcnow() +
                    datetime.timedelta(days=7)).isoformat() + 'Z'
        event_list = []
        for calendar in list_calendar(service):
            events_result = service.events().list(calendarId=calendar['id'], timeMin=time_now, timeMax=time_max,
                                                  maxResults=10, singleEvents=True,
                                                  orderBy='startTime').execute()
            events = events_result.get('items', [])

            # Prints the start and name of the next 10 events in 7 days
            for event in events:
                start = event['start'].get(
                    'dateTime', event['start'].get('date'))
                event_list.append(
                    {'dateTime': start, 'summary': event['summary']})

        def sort_datetime_strings(datetime_obj):
            # Convert datetime strings to datetime objects
            for dt in datetime_obj:
                if 'T' in dt['dateTime'] and ('+' in dt['dateTime'].split('T')[-1] or '-' in dt['dateTime'].split('T')[-1]):
                    dt['dateTime'] = datetime.datetime.fromisoformat(
                        dt['dateTime'])
                else:
                    dt['dateTime'] = datetime.datetime.strptime(
                        dt['dateTime'], '%Y-%m-%d')
                    # Add a default timezone (UTC) for naive datetimes
                    dt['dateTime'] = dt['dateTime'].replace(
                        tzinfo=datetime.timezone.utc)

            # Sort datetime objects
            sorted_datetime_objects = sorted(
                datetime_obj, key=lambda x: x['dateTime'])

            # Convert sorted datetime objects back to datetime strings
            sorted_datetime_obj = ['{0}  {1}'.format(dt['dateTime'].strftime(
                '%Y-%m-%dT%H:%M:%S%z'), dt['summary']) for dt in sorted_datetime_objects]

            return sorted_datetime_obj

        event_list = sort_datetime_strings(event_list)

        if len(event_list) == 0:
            return 'No upcoming events found.'
        else:
            return "\n".join(event_list)

    except HttpError as error:
        return f'An error occurred: {error}'


class Calendar(Handler):
    def __init__(self):
        super().__init__()

    @property
    def info(self):
        return {
            "name": "calendar",
            "version": "1.0.0",
            "author": "thisiszy",
            "commands": [
                {
                    "command": "events",
                    "description": r"View your next events, usage: /events",
                },
                {
                    "command": "auth",
                    "description": r"Authorize the bot to access your Google Calendar, usage: /auth <secret\_token\>",
                },
                {
                    "command": "delete",
                    "description": r"Delete your Google Calendar authorization, usage: /delete <event\_id\>",
                }
            ]
        }

    @command_handler
    @restricted
    async def events(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        result = list_events(update.effective_chat.id)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=result)

    @command_handler
    @restricted
    async def auth(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        token = update.message.text.strip("/auth").strip(" ")
        creds = update_token_crediential(
            update.effective_chat.id, token, force_update=True)
        if creds is None:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Token invalid")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Token saved")

    @command_handler
    @restricted
    async def delete(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        event_id = update.message.text.strip("/delete").strip(" ")
        user_id = update.effective_chat.id
        if event_id == "":
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Please specify the event id")
            return

        try:
            creds = update_token_crediential(user_id, None)
        except exceptions.RefreshError:
            c.execute('SELECT token FROM tokens WHERE user_id = ?', (user_id,))
            result = c.fetchone()
            if result:
                creds = update_token_crediential(
                    user_id, result[0], force_update=True)
            else:
                raise exceptions.RefreshError
        if creds is None:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Token invalid")
        else:
            service = build('calendar', 'v3', credentials=creds)
            try:
                calendar_list = service.calendarList().list(pageToken=None).execute()
                calendar_id = calendar_list['items'][0]['id']
                service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
                await context.bot.send_message(chat_id=update.effective_chat.id, text="Event deleted")
            except Exception as error:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=f'An error occurred: {error}')
