from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
import logging
import re
from datetime import datetime

def get_info():
    return {
        "name": "datetime_extract", 
        "version": "1.0.0", 
        "author": "datetime_extract",
        "description": "*datetime\_extract*",
        "commands": ["alive"]
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

# Define function to extract time range from text
def extract_date_time(text):
    # Define regular expression to match time range string
    time_regex = r'(\d{1,2})(am|pm)\sto\s(\d{1,2})(am|pm)'
    
    # Define function to parse time strings
    def parse_time(time_str):
        return datetime.strptime(time_str, '%I%p').time()
    
    # Define list to store extracted time ranges
    results = []
    
    # Find all matches of time range string
    time_match = re.search(time_regex, text.lower())
    
    # Extract start and end time strings and parse them into time objects
    if time_match:
        start_time_str = f"{time_match.group(1)}{time_match.group(2)}"
        end_time_str = f"{time_match.group(3)}{time_match.group(4)}"
        try:
            start_time = parse_time(start_time_str)
            end_time = parse_time(end_time_str)
            results.append((start_time, end_time))
        except ValueError:
            pass
        
    # Return list of extracted time ranges
    return results

async def time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text:
        # Tokenize the text into sentences
        print(extract_date_time(update.message.text))
        
        await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me 1!")
