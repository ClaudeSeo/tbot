# -*- coding: utf-8 -*-

config = {
    'dev' : {
        'token' : ''
    }
}

def get_config(key, mode='dev'):
    return config[mode].get(key)
