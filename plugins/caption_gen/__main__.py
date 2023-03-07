from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, CommandHandler, ConversationHandler, CallbackQueryHandler
import logging
import whisper
import requests
import json
import re
import os
import configparser
config = configparser.ConfigParser()
config.read('config.ini')
base_path = config['CAPTION_GEN']['BASE_PATH']

# Set up the SQLite database
import sqlite3
conn = sqlite3.connect('storage.db')
c = conn.cursor()
c.execute('''
    CREATE TABLE IF NOT EXISTS courses
    (course_id TEXT PRIMARY KEY, username TEXT, password TEXT)
''')

RUNNING = 1

def get_info():
    return {
        "name": "caption_gen", 
        "version": "1.0.0", 
        "author": "thisiszy",
        "description": "*caption generation*: Feed the video link and get the caption, use command /caption <video link\> to add caption, use /videoauth <lecture\_id\> <username\> <password\> to set username and password\(only support video\.ethz\.ch now\)",
        "commands": ["videoauth"],
        "message_type": ["text"]
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
    # handlers.append(CallbackQueryHandler(transcribe_callback, pattern='^transcribe$'))
    handlers.append(ConversationHandler(
        entry_points=[CommandHandler("caption", caption)],
        states={
            RUNNING: [CallbackQueryHandler(transcribe_callback)],
        },
        fallbacks=[CommandHandler("stoptranscribe", cancel)],
    ))
    return handlers, info

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    await update.message.reply_text(
        "Cancel transcribe."
    )
    return ConversationHandler.END

def download_file(url, local_filename):
    # NOTE the stream=True parameter below
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192): 
                # If you have chunk encoded response uncomment if
                # and set chunk_size parameter to None.
                #if chunk: 
                f.write(chunk)
    return local_filename

async def videoauth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    inputs = update.message.text.strip("/videoauth").strip(" ")
    try:
        course_id = inputs.split(" ")[0]
        username = inputs.split(" ")[1]
        password = inputs.split(" ")[2]
        c.execute('INSERT OR REPLACE INTO courses (course_id, username, password) VALUES (?, ?, ?)', (course_id, username, password))
        conn.commit()
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Updated", reply_to_message_id=update.message.message_id)
    except IndexError:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Wrong input, use /videoauth <lecture_id> <username> <password>", reply_to_message_id=update.message.message_id)
        return


async def caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        web_link = update.message.text.strip("/caption").strip(" ")
        course_id = web_link.split("/")[-2]
        episode_id = web_link.split("/")[-1].split(".")[0]
    except IndexError:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Wrong input, use /caption <video link>", reply_to_message_id=update.message.message_id)
        return ConversationHandler.END
    
    videos = Videos(web_link)
    if not videos.is_open():
        c.execute('SELECT username, password FROM courses WHERE course_id = ?', (course_id,))
        result = c.fetchone()
        if result:
            username = result[0]
            password = result[1]
        else:
            last_msg = await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Use following command to set username and password", reply_to_message_id=update.message.message_id)
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"/videoauth {course_id}", reply_to_message_id=last_msg.message_id)
            return ConversationHandler.END

    try:
        place_holder = await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Retrieving metadata...", reply_to_message_id=update.message.message_id)
        if not videos.is_open() and not videos.login(username, password):
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Login Failed, please update your username and password by /videoauth <lecture_id> <username> <password>", reply_to_message_id=update.message.message_id)
            return ConversationHandler.END
        res = videos.json_data(episode_id)
        video_links = res['selectedEpisode']['media']['presentations']
        keyboard = []
        for num, link in enumerate(video_links):
            keyboard.append([InlineKeyboardButton(f"{link['width']}x{link['height']}", callback_data=num)])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.edit_message_text(
            chat_id=place_holder.chat_id,
            message_id=place_holder.message_id,
            text="Choose a resolution",
            reply_markup=reply_markup
        )
        
        context.user_data["video_links"] = video_links
        context.user_data["info"] = (course_id, videos.get_title(episode_id), place_holder)
        return RUNNING
        
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error {e}", reply_to_message_id=update.message.message_id)
        return ConversationHandler.END

async def transcribe_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    video_links = context.user_data["video_links"]
    course_id, video_title, place_holder = context.user_data["info"]
    selected_link = video_links[int(update.callback_query.data)]['url']
    filefolder = os.path.join(base_path, course_id)
    if not os.path.exists(filefolder):
        os.makedirs(filefolder)
    filename = video_title+"."+selected_link.split(".")[-1]
    filepath = os.path.join(filefolder, filename)
    await context.bot.edit_message_text(
        chat_id=place_holder.chat_id,
        message_id=place_holder.message_id,
        text=f"Downloading {filename}",
    )
    download_file(selected_link, filepath)
    
    await context.bot.edit_message_text(chat_id=place_holder.chat_id, message_id=place_holder.message_id, text=f"Transcribing {filename}...")
    model = whisper.load_model("small", download_root="env/share/whisper")
    result = model.transcribe(filepath)
    from whisper.utils import get_writer
    writer = get_writer("srt", os.path.dirname(filepath))
    writer(result, filename.split(".")[0])

    await context.bot.edit_message_text(chat_id=place_holder.chat_id, message_id=place_holder.message_id, text=f"Transcribed {filename}")
    return ConversationHandler.END

###################################################################
# below part is from https://github.com/plaf2000/ethz-video-lister#
###################################################################
class InvalidUrl(ValueError):
    def __init__(self,url):
        super().__init__(f"The url {url} doesn't match the expected pattern.")

class UnableToLogin(RuntimeError):
    def __init__(self,msg: str):
        super().__init__(f"Unable to login. {msg}")

class InvalidAuth(UnableToLogin):
    def __init__(self):
        super().__init__("Invalid values. Check your username and password.")
    
class UnknownAuthMethod(UnableToLogin):
    def __init__(self):
        super().__init__("Unknown authentication method.")

class Videos:
    def __init__(self, raw_url: str):
        """
            Parameters
            ----------
             - `raw_url`: url matching following pattern: `https?://video.ethz.ch/lectures/d-\w{3,6}/\d{4}/(spring|autumn)/\d{3}-\d{4}-\d{2}L`
        """

        re_base = re.match(r"https?://video.ethz.ch/lectures/d-\w{3,6}/\d{4}/(spring|autumn)/\d{3}-\d{4}-\d{2}L",raw_url)
        if re_base is None:
            raise InvalidUrl(raw_url)
        self.base_url=re_base.group(0)
        self.referer_url = f"{self.base_url}.html"
        self.base_header = {
            "Host": "video.ethz.ch",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:101.0) Gecko/20100101 Firefox/101.0",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": self.referer_url,
            "Connection": "keep-alive",
            "Sec-Fetch-Site": "same-origin",

        }
        self.videos_header =  {**self.base_header, **{
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-User": "?1",
        }}
        self.auth_cookies = None

        self.last = self.json_data()
        self.episodes  = self.last["episodes"][::-1]

        self.id2title = {}
        for episode in self.episodes:
            self.id2title[episode["id"]] = f"{episode['title']} {episode['createdAt'].replace(':','')}"

        self.username = None
        self.password = None

    def get_title(self, episode_id: int):
        return self.id2title[episode_id]
    
    def json_data(self, episode_id = None):
        """
            Parameters
            ----------
             - `episode_id`: id of the episode you want to get the data from.
        """

        episode = f"/{episode_id}" if episode_id is not None else ""
        data_url = f"{self.base_url}{episode}.series-metadata.json"
        req = requests.get(data_url, headers=self.videos_header, cookies=self.auth_cookies)
        return json.loads(req.text)

    def get_presentations(self):
        presentations = []
        for episode in self.episodes:
            presentations.append(self.json_data(episode["id"])["selectedEpisode"]["media"]["presentations"])
        return presentations


    def is_open(self):
        """            
            Returns
            -------
            True if the videos are open and there's no need to be logged in.
        """
        return self.last["protection"] == "NONE"

    def set_auth_cookies(self, username, password):
        """
            Parameters
            ----------
             - `username`: the username
             - `password`: the password
            
            Returns
            -------
            The authorisation's cookies.
        """

        if self.is_open():
            return self.auth_cookies

        auth_headers = {**self.base_header, **{
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/x-www-form-urlencoded",
            "Content-Length": "41",
            "Origin": "https://video.ethz.ch",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
        }}

        self.protection = self.last["protection"]

        if self.protection == "PWD":
            self.username = username
            self.password = password
            login_url: str = f"{self.base_url}.series-login.json"
            data = {"_charset_": "utf-8", "username": self.username,
                "password": self.password}

            

            auth_req = requests.post(login_url, headers=auth_headers, data=data)


            try:
                success = json.loads(auth_req.text)["success"]
            except json.decoder.JSONDecodeError:
                raise InvalidAuth()
            
        elif self.protection =="ETH":
            self.username = username
            self.password = password

            login_url: str = f"{self.base_url}/j_security_check"

            data = {"_charset_": "utf-8", "j_username": self.username,
                "j_password": self.password, "j_validate": "true"}

            auth_headers = {**auth_headers, **{
                "CSRF-Token": "undefined",
                "Content-Length": "57",
                "DNT": "1",
            }}

            auth_req = requests.post(login_url, headers=auth_headers, data=data)
            success = not "invalid_login" in auth_req.text
        else:
            raise UnknownAuthMethod()            

        if not success:
            raise InvalidAuth()
        self.auth_cookies =  auth_req.cookies
        return self.auth_cookies


    def login(self, username = None, password = None):
        """
            Open a login form on the shell.

            Returns
            -------
            `True` on success, else keep asking for username and password (unless authentication method is unknown).
        """
        if self.is_open():
            print("Open-access videos. No need to login.")
        else:
            try:
                self.set_auth_cookies(username,password)
            except UnknownAuthMethod as e:
                print(e)
                return False
            except InvalidAuth as e:
                print(e)
                return self.login(username, password)
        return True
