from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
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

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Set up the SQLite database
conn = sqlite3.connect('storage.db')
c = conn.cursor()
c.execute('''
    CREATE TABLE IF NOT EXISTS tokens
    (user_id INTEGER PRIMARY KEY, token TEXT, credentials TEXT)
''')

def get_info():
    return {
        "name": "calendar", 
        "version": "1.0.0", 
        "author": "thisiszy",
        "description": "*google calendar operation*: view your next events by /events, authorize the bot to access your Google Calendar by /auth <secret token\>, delete your Google Calendar authorization by /delete <event\_id\>",
        "commands": ["events", "auth", "delete"]
    }

def get_handlers(command_list):
    info = get_info()
    handlers = []
    loaded_commands = []
    for command in info['commands']:
        if command in command_list:
            logging.log(logging.ERROR, f"Command {command} already exists, ignored!")
            continue
        handlers.append(CommandHandler(command, eval(command)))
        loaded_commands.append(command)
        command_list.append(command)
    logging.log(logging.INFO, f"Loaded plugin {info['name']}, commands: {loaded_commands}")
    return handlers, info


def update_token_crediential(user_id, secret):
    creds = None
    # The database stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    c.execute('SELECT token, credentials FROM tokens WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    if result:
        creds = Credentials.from_authorized_user_info(json.loads(result[1]), SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if secret is not None:
                flow = InstalledAppFlow.from_client_config(json.loads(secret), SCOPES)
            else:
                if result:
                    secret = result[0]
                    flow = InstalledAppFlow.from_client_config(json.loads(secret), SCOPES)
                else:
                    return None
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        c.execute('INSERT OR REPLACE INTO tokens (user_id, token, credentials) VALUES (?, ?, ?)', (user_id, secret, creds.to_json()))
        conn.commit()
    return creds


def list_events(user_id):
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = update_token_crediential(user_id, None)
    if creds is None:
        return "Please authorize the bot to access your Google Calendar by /auth <secret token>"
    try:
        service = build('calendar', 'v3', credentials=creds)

        # Call the Calendar API
        now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        events_result = service.events().list(calendarId='primary', timeMin=now,
                                              maxResults=10, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])

        if not events:
            return 'No upcoming events found.'

        # Prints the start and name of the next 10 events
        event_list = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            event_list.append(f"{start} {event['summary']}")
        return "\n".join(event_list)

    except HttpError as error:
        return f'An error occurred: {error}'

async def events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = list_events(update.effective_chat.id)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=result)

async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token = update.message.text.strip("/auth").strip(" ")
    creds = update_token_crediential(update.effective_chat.id, token)
    if creds is None:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Token invalid")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Token saved")

async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    event_id = update.message.text.strip("/delete").strip(" ")
    creds = update_token_crediential(update.effective_chat.id, None)
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