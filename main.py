import mysql.connector
import configparser
import logging

import telegram
from flask import Flask, request
from telegram.ext import Dispatcher, MessageHandler, Filters
from GPASpider import Spider_gpa
import psutil

# Load data from config.ini file
config = configparser.ConfigParser()
config.read('config.ini')

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Initial Flask app
app = Flask(__name__)

# Initial bot by Telegram access token
proxy = telegram.utils.request.Request(proxy_url='socks5://127.0.0.1:1025')
bot = telegram.Bot(token=(config['TELEGRAM']['ACCESS_TOKEN']), request=proxy)
# bot = telegram.Bot(token=(config['TELEGRAM']['ACCESS_TOKEN']))

# Initial database
mydb = mysql.connector.connect(
  host="localhost",
  user=config['MYSQL']['USER_NAME'],
  password=config['MYSQL']['PASSWORD'],
  database="mydatabase",
  auth_plugin="mysql_native_password"
)
mycursor = mydb.cursor()


@app.route('/hook', methods=['POST'])
def webhook_handler():
    """Set route /hook with POST method will trigger this method."""
    if request.method == "POST":
        update = telegram.Update.de_json(request.get_json(force=True), bot)

        # Update dispatcher process that handler to process this message
        dispatcher.process_update(update)
    return 'ok'


def getgpa(update):
    sql = "SELECT * FROM user WHERE tgid = %s"
    adr = (update.message.chat.id,)

    mycursor.execute(sql, adr)
    query_result = mycursor.fetchall()
    if not query_result:
        update.message.reply_text("Your id is not in the database, please use /setinfo")
    else:
        scores, GPA_weighted, score_weighted, score_average, GPA_4_weighted = Spider_gpa(query_result[0][2], query_result[0][3])
        update.message.reply_text("GPA_weighted: "+str(GPA_weighted)+
                                  "\nscore_weighted: "+str(score_weighted)+
                                  "\nscore_average: "+str(score_average)+
                                  "\nGPA_4_weighted: "+str(GPA_4_weighted))


def setinfo(update):
    content = update.message.text.split(' ')
    if len(content) != 3:
        update.message.reply_text("Please enter your studentID(PBxxxxxxxx) and password \n"
                                  "studentID and password should divide by space \n Example:PBxxxxxxxx 123456")
    else:
        sql = "SELECT * FROM user WHERE tgid = %s"
        adr = (update.message.chat.id,)
        mycursor.execute(sql, adr)
        query_result = mycursor.fetchall()
        if not query_result:
            sql = "INSERT INTO user (tgid, username, pwd) VALUES (%s, %s, %s)"
            val = (update.message.chat.id, content[1], content[2])
            mycursor.execute(sql, val)
            mydb.commit()
            update.message.reply_text("Add successfully")
        else:
            sql = "UPDATE user SET username = %s, pwd = %s WHERE tgid = %s"
            val = (content[1], content[2], update.message.chat.id)
            mycursor.execute(sql, val)
            mydb.commit()
            update.message.reply_text("Update successfully")


def get_sysinfo(update):
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage('/')
    message = "*[memory]*" + "\n"\
              + "*total:* " + str(format(mem.total/1048576, '.1f')) + " MB" + "\n"\
              + "*used: *" + str(format(mem.used/1048576, '.1f')) + " MB" + "\n"\
              + "*percent: *" + str(format(mem.percent, '.1f')) + "%" + "\n"\
              + "*[swap]*" + "\n"\
              + "*total:* " + str(format(swap.total/1048576, '.1f')) + " MB" + "\n"\
              + "*used: *" + str(format(swap.used/1048576, '.1f')) + " MB" + "\n"\
              + "*percent: *" + str(format(swap.percent, '.1f')) + "%" + "\n"\
              + "*[disk]*" + "\n"\
              + "*total:* " + str(format(disk.total/1073741824, '.1f')) + " GB" + "\n"\
              + "*used: *" + str(format(disk.used/1073741824, '.1f')) + " GB" + "\n"\
              + "*free: *" + str(format(disk.free/1073741824, '.1f')) + " GB" + "\n"\
              + "*percent: *" + str(disk.percent) + "%" + "\n"\
              + "*[cpu]*" + "\n"\
              + "*cpu usage: *" + str(psutil.cpu_percent(percpu=False)) + "\n"\
              + "*each cpu usage:* " + str(psutil.cpu_percent(percpu=True)).strip('[]')
    update.message.reply_text(message, parse_mode='Markdown')


def command_phrase(text, update):
    """select command need to be execute"""
    if text == "/setinfo":
        setinfo(update)
    elif text == "/getgpa":
        getgpa(update)
    elif text == "/getsysinfo":
        get_sysinfo(update)
    else:
        update.message.reply_text(update.message.text)


def private_reply_handler(bot, update):
    """Reply private message."""
    print(update)
    text = update.message.text.split(' ')[0]
    command_phrase(text, update)


def group_reply_handler(bot, update):
    """Reply group message."""
    print(update)
    # text = update.message.text.split(' ')[0]
    # command_phrase(text, update)
    update.message.reply_text("in group")


# New a dispatcher for bot
dispatcher = Dispatcher(bot, None)

# Add handler for handling message, there are many kinds of message. For this handler, it particular handle text
# message.
dispatcher.add_handler(MessageHandler(Filters.private, private_reply_handler))
dispatcher.add_handler(MessageHandler(Filters.group, group_reply_handler))

if __name__ == "__main__":
    # Running server
    app.run(debug=True)
