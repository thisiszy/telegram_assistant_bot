from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
import logging
import urllib.request, json 
from xml.etree.ElementTree import parse, fromstring
import sys
import datetime
import argparse
import certifi
import ssl

def get_info():
    return {
        "name": "mensa", 
        "version": "1.0.0", 
        "author": "thisiszy",
        "description": "*mensa*: Use /mensa [location] command to check todays menu\.",
        "commands": ["mensa"]
    }

# return handlers list
def get_handlers(command_list):
    info = get_info()
    handlers = [CommandHandler("mensa", alive)]
    if "mensa" in command_list:
        logging.log(logging.ERROR, f"Command {command} already exists, ignored!")
        return []
    logging.log(logging.INFO, f"Loaded plugin mensa, commands: mensa")
    return handlers, info


class uzh_mensa:
    def __init__(self, args, meta_link="https://raw.githubusercontent.com/famoser/Mensa/master/app/src/main/assets/uzh/locations_rss.json"):
        self.args = args
        self.uzh_mensa_list = []
        uzh_meta_data_url = meta_link
        context = ssl.create_default_context(cafile=certifi.where())
        with urllib.request.urlopen(uzh_meta_data_url, context=context) as url:
            uzh_meta_data = json.loads(url.read().decode())
            for campus in uzh_meta_data:
                self.uzh_mensa_list += campus['mensas']

    def print_uzh_menus(self, target_date, condition=None):
        mensa_list = []
        for mensa in self.uzh_mensa_list:
            if condition is not None:
                if condition not in mensa['title'].lower() and condition not in mensa['infoUrlSlug'].lower():
                    continue
            # print(bcolors.OKGREEN, bcolors.BOLD, mensa['title'], bcolors.ENDC)
            cur_mensa = {'status': 'ok'}
            formatted_text = ""
            formatted_text += "*{title}*\n".format(title=mensa['title'])
            
            weekday = target_date.weekday()+1

            if self.args.lang == 'en':
                uzh_url = 'http://zfv.ch/de/menus/rssMenuPlan?menuId={}&dayOfWeek={}'.format(mensa['idSlugEn'], str(weekday))
            elif self.args.lang == 'de':
                uzh_url = 'http://zfv.ch/de/menus/rssMenuPlan?menuId={}&dayOfWeek={}'.format(mensa['idSlugDe'], str(weekday))
            else:
                cur_mensa['status'] = 'Language not supported'
                return cur_mensa

            context = ssl.create_default_context(cafile=certifi.where())
            with urllib.request.urlopen(uzh_url, context=context) as url:
                string = url.read().decode()
                string= string.replace('<br />', '') # fix malformed tags
                document= fromstring(string) # parse the string

                i = 0
                if len(document[4][3][0]) != 0:
                    for child in document[4][3][0]:
                        if(i%2 == 0):
                            title = child.text
                            price = child[0].text

                            cleanTitle = " ".join(title.split())
                            cleanPrice = " ".join(price.split())[2:10]
                            # print(bcolors.OKBLUE, bcolors.BOLD, cleanTitle, cleanPrice, bcolors.ENDC)
                            formatted_text += "`{title} | {price}`\n".format(title=cleanTitle, price=cleanPrice)
                        else:
                            description = child.text
                            cleanDescription = " ".join(description.split())
                            # print("    ",cleanDescription)
                            formatted_text += "    {description}\n".format(description=cleanDescription)
                        i += 1
                else:
                    # print(bcolors.BOLD, bcolors.FAIL, mensa['title'], "CLOSED", bcolors.ENDC)
                    formatted_text += "{title} CLOSED\n".format(title=mensa['title'])
            # print("--------------------------------------------------------------------")
            cur_mensa['text'] = formatted_text
            mensa_list.append(cur_mensa)

        return mensa_list


class eth_mensa:
    def __init__(self, args, meta_link='''https://idapps.ethz.ch/cookpit-pub-services/v1/facilities?client-id=ethz-wcms&lang={lang}&rs-first={rs_first}&rs-size={rs_size}''', data_link='''https://idapps.ethz.ch/cookpit-pub-services/v1/weeklyrotas?client-id=ethz-wcms&lang={lang}&rs-first={rs_first}&rs-size={rs_size}&valid-after={valid_after}'''):
        self.args = args
        self.meta_link = meta_link
        self.data_link = data_link
        facilities = self.request_eth_facilities_list(lang=self.args.lang)
        facilities.sort(key=lambda x: x['facility-id'])
        self.id_to_eth_mensa = {f['facility-id']: f for f in facilities}


    def request_eth_facilities_list(self, rs_size=50, rs_first=0, lang="en"):
        eth_url = self.meta_link.format(lang=lang, rs_first=rs_first, rs_size=rs_size)
        
        context = ssl.create_default_context(cafile=certifi.where())
        with urllib.request.urlopen(eth_url, context=context) as url:
            data = json.loads(url.read().decode())['facility-array']
        assert len(data) < rs_size  # if rs_size equals len(data), then there are more facilities to be requested

        return data

    def print_eth_menus(self, target_date, condition):
        mensa_list = []
        def request_weekly_menus(rs_first, rs_size, valid_after):
            eth_url = self.data_link.format(lang=self.args.lang, rs_first=rs_first, rs_size=rs_size, valid_after=valid_after)
            context = ssl.create_default_context(cafile=certifi.where())
            with urllib.request.urlopen(eth_url, context=context) as url:
                data = json.loads(url.read().decode())['weekly-rota-array']
            
            return data

        eth_menu_data = request_weekly_menus(0, 50, target_date.strftime("%Y-%m-%d"))

        valid_data = [i for i in eth_menu_data if (datetime.datetime.strptime(i['valid-from'], "%Y-%m-%d").date() <= target_date and ('valid-to' not in i or datetime.datetime.strptime(i['valid-to'], "%Y-%m-%d").date() >= target_date))]
        valid_data.sort(key=lambda x: x['facility-id'])

        for item in valid_data:
            if condition is not None:
                if condition not in self.id_to_eth_mensa[item['facility-id']]['facility-name'].lower() and \
                    condition not in self.id_to_eth_mensa[item['facility-id']]['facility-url'].lower():
                    continue
            target_day_menus = item['day-of-week-array'][target_date.weekday()]
            is_open = True
            cur_mensa = {'status': 'ok'}
            formatted_text = ""
            if 'opening-hour-array' in target_day_menus:
                for opening_hours in target_day_menus['opening-hour-array']:
                    if opening_hours['meal-time-array'] != []:
                        formatted_text += "*{title}*\n".format(title=self.id_to_eth_mensa[item['facility-id']]['facility-name'])
                        for opening_hour in opening_hours['meal-time-array']:
                            formatted_text += "__{name}__\t{time_from}-{time_to}\n".format(name=opening_hour['name'], time_from=opening_hour['time-from'], time_to=opening_hour['time-to'])
                            if 'line-array' in opening_hour:
                                for meal in opening_hour['line-array']:
                                    if 'meal' in meal:
                                        cur_menu = {}
                                        formatted_text += "`{name} | CHF {price}`\n".format(name=meal['meal']['name'], price='/'.join([str(price['price']) for price in meal['meal']['meal-price-array']]))
                                        formatted_text += "  {description}\n".format(description=meal['meal']['description'].replace("\n", " "))
                    else:
                        is_open = False
            else:
                is_open = False
            
            if not is_open:
                formatted_text += "{title} CLOSED\n".format(title=self.id_to_eth_mensa[item['facility-id']]['facility-name'])
            cur_mensa['text'] = formatted_text
            mensa_list.append(cur_mensa)
        
        return mensa_list


async def alive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args_list = update.message.text.strip("/mensa").strip(" ").split()

    parser = argparse.ArgumentParser()
    parser.add_argument('location', type=str, default=None, help=
            "Search any keywords that related to the mensa(use 'all' to print all mensas), e.g.: zentrum, poly, claus, irchel")
    parser.add_argument('-d', '--day', type=str, default=None, help="YYYY-MM-DD")
    parser.add_argument('-l', '--lang', type=str, default='en', help="en or de")
    try:
        args = parser.parse_args(args_list)
        args.location = args.location.lower()
        if args.location == 'all':
            args.location = None

        if args.day is None:
            target_date = datetime.date.today()
        else:
            target_date = datetime.datetime.strptime(args.day, "%Y-%m-%d").date()
        weekday = target_date.weekday()

        emensa = eth_mensa(args)
        umensa = uzh_mensa(args)

        emensa_list = emensa.print_eth_menus(target_date, args.location)
        logging.log(logging.INFO, emensa_list)
        umensa_list = umensa.print_uzh_menus(target_date, args.location)
        logging.log(logging.INFO, umensa_list)

        # msg = emsg + umsg
        mensa_list = emensa_list + umensa_list
        msg = ""
        for mensa in mensa_list:
            if mensa['status'] == 'ok':
                next_msg = mensa['text']
                if len(msg + next_msg) > 4000:
                    msg = msg.replace("-", r"\-").replace("|", r"\|").replace("!", r"\!").replace("(", r"\(").replace(")", r"\)").replace("+", r"\+").replace(".", r"\.")
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode="MarkdownV2")
                    msg = next_msg

                msg += next_msg + "\n"
            else:
                msg = mensa['status']
                break
        if len(mensa_list) == 0:
            msg = "No menu found"
            await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
        elif len(msg) > 0:
            msg = msg.replace("-", r"\-").replace("|", r"\|").replace("!", r"\!").replace("(", r"\(").replace(")", r"\)").replace("+", r"\+").replace(".", r"\.")
            await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode="MarkdownV2")
    except SystemExit:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Argument Error: Use /mensa [location] command to check todays menu")
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f'An error occurred: {e}')