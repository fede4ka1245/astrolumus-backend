import urllib
import requests
from selectolax.parser import HTMLParser

from .format_date import format_date
from ..helpers.values import LOGIN_URL, payload
from .parse_dashi_table import parse_dashi_table
from ..helpers.format_datetime import format_datetime
from datetime import datetime
import locale


def get_dashi(
        name_user,
        dt,
        part_world,
        tz_hour,
        tz_minutes,
        latitude,
        longitude,
        name,
        dt_start
):
    session = requests.Session()
    session.post(LOGIN_URL, data=payload)

    params = {
        'name': name_user,
        'dt': format_datetime(dt),
        'tp': 'j',
        'lat': latitude,
        'lon': longitude,
        'id': '',
        'fetch': 'dasa',
        'data': f'dasa_system={name}',
        'tz': f'{part_world}{tz_hour}:{tz_minutes}',
    }

    if dt_start is not None:
        params['data'] = f'dasa_system={name}&start_date={dt_start.strftime("%Y-%m-%d")}+{dt.strftime("%H:%M:%S")}&sade_sati='

    response = session.get('https://j108.ru/?' + urllib.parse.urlencode(params))

    if response.json().get("success") is False:
        return {
            "error": response.text
        }

    html = HTMLParser(response.json().get("html"))

    table = parse_dashi_table(html)

    locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')

    dateEnd = table[-1]['dateEnd']
    dateStart = table[0]['dateStart']

    return {
        "table": table,
        "dateEnd": f"{datetime.strptime(dateEnd, '%d/%m/%Y').strftime('%Y-%m-%d')}T{table[-1]['timeEnd']}",
        "dateStart": f"{datetime.strptime(dateStart, '%d/%m/%Y').strftime('%Y-%m-%d')}T{table[0]['timeStart']}",
    }
