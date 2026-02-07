import urllib
import requests
from ..helpers.values import LOGIN_URL, payload
from bs4 import BeautifulSoup
from .parse_sarvatobhadra import parse_sarvatobhadra
from .parse_chakra import parse_chakra
from ..helpers.format_datetime import format_datetime


def get_chakra(
    name_user,
    dt,
    part_world,
    tz_hour,
    tz_minutes,
    latitude,
    longitude,
    chakra,
    chakra_dt,
    chakra_part_world,
    chakra_tz_hour,
    chakra_tz_minutes,
    nakshatra_start_point,
    start_point
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
        'fetch': 'chakra',
        'data': 'dasa_system=chakra',
        'chakra': chakra,
        'tz': f'{part_world}{tz_hour}:{tz_minutes}',
        'gochara[dt]': format_datetime(chakra_dt).replace('+', ' '),
        'gochara[tz][z]': chakra_part_world,
        'gochara[tz][h]': chakra_tz_hour,
        'gochara[tz][i]': chakra_tz_minutes,
    }

    if start_point is not None:
        params['gochara[start_point]'] = start_point

    if nakshatra_start_point is not None:
        params['gochara[start_nakshatra]'] = nakshatra_start_point

    url = f'https://j108.ru/?{urllib.parse.urlencode(params, True)}'

    soap = BeautifulSoup(session.get(url).json().get('html'))

    if chakra == 'sarvatobhadra':
        return parse_sarvatobhadra(soap)

    return parse_chakra(soap)
