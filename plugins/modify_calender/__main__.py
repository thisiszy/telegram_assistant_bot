from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
import logging

# use google calendar
import datetime
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_info():
    return {
        "name": "modify_calender", 
        "version": "1.0.0", 
        "author": "thisiszy",
        "description": "*view, edit your google calender items*: view your next events by /events",
        "commands": ["events"]
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

def list_events():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
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
    result = list_events()
    await context.bot.send_message(chat_id=update.effective_chat.id, text=result)
