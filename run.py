# -*- coding: utf-8 -*-
import requests
import logging
import re
from urllib2 import quote
from bs4 import BeautifulSoup
from telegram.ext import Updater, CommandHandler
from config import get_config 

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

def get_overlog_uid(query):
    url = 'https://overlog.net/leaderboards/global/score?q=%s' % quote(query.encode('utf-8'))
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    t = soup.find('table', class_='table-striped').find('tbody')
    tr = t.find('tr')
    if not tr.has_attr('data-uid'):
        return False
    return tr['data-uid']

def get_overlog_data(uid):
    entries = {'data' : []}
    url = 'https://overlog.net/detail/overview/%s' % uid
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    character = soup.find('div', class_='character')
    entries['displayName'] = character.find('p', class_='displayName').contents[0].strip()
    entries['level'] = character.find(text=re.compile('Level'))
    heros = soup.find_all(class_='heroList')[1]
    basics = heros.find_all(class_='heroBasic')
    idx = 0
    for basic in basics[:3]:
        entry = {}
        idx += 1
        entry['idx'] = idx
        entry['name'] = basic.find('span', class_='name').get_text()
        entry['playTime'] = basic.find('td', class_='timePlayed').get_text().strip()
        entry['kda'] = basic.find('span', class_='rate').get_text()
        entry['ratio'] = basic.find('span', class_='ratio').get_text()
        entry['objective'] = basic.find(class_='objective').contents[2].strip()
        entries['data'].append(entry)
    return entries

def overlog(bot, update):
    chat_id = update.message.chat_id
    query = update.message.text.split('/w')[1].strip()
    uid = get_overlog_uid(query)
    if not uid: 
        bot.sendMessage(update.message.chat_id, text='등록된 프로필이 없습니다. "Overwatch#1234"와 같이 뒤에 숫자까지 함께 입력하여 검색하시기 바랍니다. 대소문자를 구분합니다')
        return
    entries = get_overlog_data(uid)
    text = '%s[%s]' % (entries['displayName'], entries['level'])
    text += '\n\n'
    for entry in entries['data'] :
        text += '%d. %s(%s)\n' % (entry['idx'], entry['name'], entry['playTime'])
        text += 'kda : %s %s : %s %s : %s\n' % (entry['kda'], '승률'.decode('utf-8'), entry['ratio'], '평균 임무기여'.decode('utf-8'), entry['objective'])
    bot.sendMessage(update.message.chat_id, text=text)

def echo(bot, update):
    bot.sendMessage(update.message.chat_id, text='Hi!')

def main() :
    updater = Updater(get_config('token'))
    dp = updater.dispatcher
    dp.add_handler(CommandHandler('echo', echo))
    dp.add_handler(CommandHandler('w', overlog))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__' :
    main()
