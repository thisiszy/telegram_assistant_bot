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

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Set up the SQLite database
conn = sqlite3.connect('storage.db')
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
        c.execute('SELECT token, credentials FROM tokens WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        secret = result[0]
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
                    if secret is not None:
                        flow = InstalledAppFlow.from_client_config(json.loads(secret), SCOPES)
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
        c.execute('INSERT OR REPLACE INTO tokens (user_id, token, credentials) VALUES (?, ?, ?)', (user_id, secret, creds.to_json()))
        conn.commit()
    return creds

try:
    creds = update_token_crediential("5566132709", None)    # id of Courses
except exceptions.RefreshError:
    c.execute('SELECT token FROM tokens WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    if result:
        creds = update_token_crediential(user_id, result[0], force_update=True)
    else:
        raise exceptions.RefreshError
if creds is None:
    raise "Please authorize the bot to access your Google Calendar by /auth <secret token>"

service = build('calendar', 'v3', credentials=creds)

# Lesson details
summary = "Course: 0129-ETH 851-0832-10 Advanced English for academic purposes C1-C2"
description = """Lecturer: David Camorani
E-Mail: david.camorani@sprachen.uzh.ch
Location: ETH HG G 26.1, Rämistrasse 101"""

# Define the time and date of the lesson
start_time = datetime.datetime(2023, 9, 18, 12, 15, 0)
end_time = datetime.datetime(2023, 9, 18, 13, 45, 0)
time_zone = 'Europe/Zurich'

# Create the event
event = {
    'summary': summary,
    'description': description,
    'start': {
        'dateTime': start_time.isoformat(),
        'timeZone': time_zone,
    },
    'end': {
        'dateTime': end_time.isoformat(),
        'timeZone': time_zone,
    },
    'recurrence': [
        'RRULE:FREQ=WEEKLY;UNTIL=20231218T235959Z'
    ],
}

# Insert the event into the calendar

def list_calendars(service):
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

calendar_list = list_calendars(service)

print("Please select a calendar: ")
for i, calendar in enumerate(calendar_list):
    print(f"{i}: {calendar['summary']}, {calendar['id']}")

calendar_id = calendar_list[int(input())]['id']
event = service.events().insert(calendarId=calendar_id, body=event).execute()

print(f"Event created: {event.get('htmlLink')}")