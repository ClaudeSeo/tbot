# -*- coding: utf-8 -*-
import requests
from config import get_config 
from telegram.ext import Updater, CommandHandler

def echo(bot, update):
    bot.sendMessage(update.message.chat_id, text='Hi!')

def main() :
    updater = Updater(get_config('token'))
    dp = updater.dispatcher
    dp.add_handler(CommandHandler('echo', echo))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__' :
    main()
