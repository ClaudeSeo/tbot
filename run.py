# -*- coding: utf-8 -*-
import requests
import logging
import re
import os
from uuid import uuid4
from urllib2 import quote
from bs4 import BeautifulSoup
from telegram.ext import Updater, CommandHandler
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from config import get_config 

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

def get_image_from_url(url):
    r = requests.get(url)
    img = Image.open(BytesIO(r.content))
    img = img.resize((150, 150), Image.NEAREST)
    return img

def get_font(mode='key'):
    if not mode in ['key', 'value'] :
        raise ValueError('NOT MODE')
    size = 35
    if mode == 'key' :
        size = 40
    font = ImageFont.truetype('static/nanum.ttf', size)
    return font

def get_overlog_uid(query):
    url = 'https://overlog.net/leaderboards/global/score?q=%s' % quote(query.encode('utf-8'))
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    t = soup.find('table', class_='table-striped').find('tbody')
    tr = t.find('tr')
    if not tr.has_attr('data-uid'):
        return False
    return tr['data-uid']

def overlog_renew(uid):
    headers = {'content-type' : 'application/x-www-form-urlencoded; charset=UTF-8', 'origin' : 'https://overlog.net', 'referer' : 'https://overlog.net/detail/overview/' + uid, 'user-agent' : 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36'}
    url = 'https://overlog.net/detail/renew'
    body = {'uid' : uid}
    rv = requests.post(url, headers=headers, data=body).json()

def get_overlog_hero_detail(uid, hero_id):
    entry = {}
    headers = {'content-type' : 'application/x-www-form-urlencoded; charset=UTF-8', 'origin' : 'https://overlog.net', 'referer' : 'https://overlog.net/detail/overview/' + uid, 'user-agent' : 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36'}
    url = 'https://overlog.net/detail/hero/%s' % hero_id
    body = {'uid' : uid}
    rv = requests.post(url, headers=headers, data=body).json()
    if rv['error'] != 0:
        return False
    html = rv['html']
    soup = BeautifulSoup(html, 'html.parser')
    verts = soup.find_all(text=re.compile(u'영웅 기술'))
    entry['skill'] = []
    for vert in verts:
        vert = vert.parent.parent
        skill_name = vert.find('h4').get_text().split(u'영웅 기술:')[1]
        tmp_skill = vert.find('dl')
        entry['skill'].append({
            'name' : skill_name,
            'key' : tmp_skill.find('dt').get_text(),
            'value' : tmp_skill.find('dd').get_text().strip()
        })
    tmp_kill = soup.find('h4', text=re.compile(u'처치')).parent.find('dl')
    entry['kill'] = {
        'key' : tmp_kill.find('dt').get_text(),
        'value' : tmp_kill.find('dd').get_text().strip()
    }
    tmp_deal = soup.find(text=re.compile(u'딜량')).parent.parent.find_all('dl')[2]
    entry['deal'] = {
        'key' : tmp_deal.find('dt').get_text().replace(u'게임당 평균 ', ''),
        'value' : tmp_deal.find('dd').get_text().strip()
    }
    return entry

def get_overlog_data(uid):
    entries = {'data' : []}
    url = 'https://overlog.net/detail/overview/%s' % uid
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    character = soup.find('div', class_='character')
    entries['playerIcon'] = character.find('img', class_='portrait')['src']
    entries['displayName'] = character.find('p', class_='displayName').contents[0].strip()
    entries['level'] = character.find(text=re.compile('Level'))
    heros = soup.find_all(class_='heroList')[1]
    basics = heros.find_all(class_='heroBasic')
    details = heros.find_all(class_='heroDetail')
    idx = 0
    for basic in basics:
        entry = {}
        idx += 1
        entry['idx'] = idx
        entry['name'] = basic.find('span', class_='name').get_text()
        check_point = basic.find('td', class_='not_available')
        if check_point :
            entry['text'] = check_point.get_text()
        else :
            entry['playTime'] = basic.find('td', class_='timePlayed').get_text().strip()
            entry['kda'] = basic.find('span', class_='rate').get_text()
            entry['ratio'] = basic.find('span', class_='ratio').get_text()
            entry['objective'] = basic.find(class_='objective').contents[2].strip()
            entry['img'] = basic.find('img')['src']
            hero_id = basic['data-hero']
            entry['info'] = get_overlog_hero_detail(uid, hero_id)
        entries['data'].append(entry)
    return entries

def overlog(bot, update):
    chat_id = update.message.chat_id
    query = update.message.text.split('/w')[1].strip()
    uid = get_overlog_uid(query)
    if not uid: 
        bot.sendMessage(update.message.chat_id, text='등록된 프로필이 없습니다. "Overwatch#1234"와 같이 뒤에 숫자까지 함께 입력하여 검색하시기 바랍니다. 대소문자를 구분합니다')
        return
    overlog_renew(uid)
    bot.sendMessage(update.message.chat_id, text=u'%s님 데이터가 갱신되었습니다.' % (query))
    entries = get_overlog_data(uid)
    text = '%s[%s]' % (entries['displayName'], entries['level'])
    text += '\n\n'
    for entry in entries['data'][:3] :
        text += '%d. %s(%s)\n' % (entry['idx'], entry['name'], entry['playTime'])
        text += 'kda : %s %s : %s %s : %s\n' % (entry['kda'], '승률'.decode('utf-8'), entry['ratio'], '평균 임무기여'.decode('utf-8'), entry['objective'])
        text += '%s : %s\n' % (entry['info']['kill']['key'], entry['info']['kill']['value'])
        text += '%s : %s\n' % (entry['info']['deal']['key'], entry['info']['deal']['value'])
        for skill in entry['info']['skill'] :
            text += '%s(%s) : %s\n' % (skill['name'], skill['key'], skill['value'])
        text += '\n'

    bot.sendMessage(update.message.chat_id, text=text)

def add_text(draw, key, value, bg_w=50, bg_h=50):
    key_font = get_font('key')
    val_font = get_font('value')
    k_w, k_h = key_font.getsize(key) # keyword width, keyword height
    v_w, v_h = val_font.getsize(value) # value width, value height
    draw.text((bg_w, bg_h), key,fill='white', font=key_font)
    draw.text((bg_w, bg_h + k_h), value, fill='white', font=val_font)
    bg_w += k_w + 20 if k_w > v_w else v_w + 20 # margin width
    return bg_w

def overlog_img(bot, update):
    chat_id = update.message.chat_id
    query = update.message.text.split('/wi')[1].strip()
    uid = get_overlog_uid(query)
    if not uid: 
        bot.sendMessage(update.message.chat_id, text='등록된 프로필이 없습니다. "Overwatch#1234"와 같이 뒤에 숫자까지 함께 입력하여 검색하시기 바랍니다. 대소문자를 구분합니다')
        return
    overlog_renew(uid)
    bot.sendMessage(update.message.chat_id, text=u'%s님 데이터가 갱신되었습니다.' % (query))
    bot.sendMessage(update.message.chat_id, text=u'%s님 데이터 수집을 시작합니다.' % query)
    entries = get_overlog_data(uid) 
    bg_img = Image.open('static/background-1.jpg')
    draw = ImageDraw.Draw(bg_img)
    img = get_image_from_url(entries['playerIcon'])
    bg_img.paste(img, (90, 90))
    add_text(draw, entries['displayName'], entries['level'], 260, 90)
    bg_w, bg_h = 90, 310
    for entry in entries['data'][:5]:
        if 'text' in entry.keys():
            continue
        img = get_image_from_url(entry['img'])
        bg_img.paste(img, (bg_w, bg_h))

        bg_w += 170
        bg_w = add_text(draw, entry['name'], entry['playTime'], bg_w, bg_h)
        bg_w = add_text(draw, 'KDA', entry['kda'], bg_w, bg_h)
        bg_w = add_text(draw, u'승률', entry['ratio'], bg_w, bg_h)
        bg_w = add_text(draw, entry['info']['deal']['key'], entry['info']['deal']['value'], bg_w, bg_h)
        for skill in entry['info']['skill'] :
            key = '%s(%s)' % (skill['name'], skill['key'])
            bg_w = add_text(draw, key, skill['value'], bg_w, bg_h)

        # initialize
        bg_w = 90
        # bg_h += 170
        bg_h += 220
    filename = '%s.jpeg' % str(uuid4().hex)
    bg_img.save(filename, quality=60, optimize=True, progressive=True)
    bot.sendMessage(update.message.chat_id, text=u'데이터 수집이 완료되었습니다. 이미지 업로드를 시작합니다.')
    bot.send_photo(update.message.chat_id, photo=open(filename, 'rb'))
    os.remove(filename)

def echo(bot, update):
    bot.sendMessage(update.message.chat_id, text='Hi!')

def main() :
    updater = Updater(get_config('token'))
    dp = updater.dispatcher
    dp.add_handler(CommandHandler('echo', echo))
    dp.add_handler(CommandHandler('w', overlog))
    dp.add_handler(CommandHandler('wi', overlog_img))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__' :
    main()
