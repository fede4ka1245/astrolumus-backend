import urllib
import requests
from ..helpers.values import LOGIN_URL, payload, table_class_names
from bs4 import BeautifulSoup
from ..helpers.parse_tables import parse_tables
from ..helpers.format_datetime import format_datetime


def get_chakras_horoscope(name_user, dt, part_world, tz_hour, tz_minutes, latitude, longitude):
    session = requests.Session()
    session.post(LOGIN_URL, data=payload)

    params = {
        'name': name_user,
        'dt': format_datetime(dt),
        'tp': 'j',
        'lat': latitude,
        'lon': longitude,
        'tz': f'{part_world}{tz_hour}:{tz_minutes}',
        'id': '',
        'chakras[]': table_class_names,
        'fetch': 'varga'
    }

    url = f'https://j108.ru/?{urllib.parse.urlencode(params, True)}'

    soap = BeautifulSoup(session.get(url).json().get('html'))

    return parse_tables(soap)
