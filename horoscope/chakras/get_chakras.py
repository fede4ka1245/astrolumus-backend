import urllib
import requests
from ..helpers.values import LOGIN_URL, payload
from bs4 import BeautifulSoup
from .parse_sarvatobhadra import parse_sarvatobhadra
from .parse_chakra import parse_chakra
from .parse_sudarsana import parse_sudarsana
from ..helpers.format_datetime import format_datetime

def get_chakras(name_user, dt, part_world, tz_hour, tz_minutes, latitude, longitude):
    session = requests.Session()
    session.post(LOGIN_URL, data=payload)

    headers = {'Content-type': 'application/json', 'Accept': 'application/json'}

    params = {
        'name': name_user,
        'dt': format_datetime(dt),
        'tp': 'j',
        'lat': latitude,
        'lon': longitude,
        'id': '',
        'fetch': 'chakra',
        'data': 'dasa_system=chakra',
        'tz': f'{part_world}{tz_hour}:{tz_minutes}'
    }

    url = f'https://j108.ru/?{urllib.parse.urlencode(params, True)}'
    data = session.get(url, headers=headers).json().get('html')

    chakras_soap = BeautifulSoup(data)

    surya_calanala_soap = chakras_soap.find('div', {'class': 'box-surya-kalanala'}).findAll('div', {'class': 'n'})
    chandra_kalanala_soap = chakras_soap.find('div', {'class': 'box-chandra-kalanala'}).findAll('div', {'class': 'n'})
    sani_soap = chakras_soap.find('div', {'class': 'box-sani'}).findAll('div', {'class': 'n'})
    sarvatobhadra_children = chakras_soap.find('div', {'class': 'chakra-box-result'})

    response = {
        'sarvatobhadra': parse_sarvatobhadra(sarvatobhadra_children),
        'suryaKalanala': parse_chakra(surya_calanala_soap),
        'chandraKalanala': parse_chakra(chandra_kalanala_soap),
        'sani': parse_chakra(sani_soap),
        'sudarsana': parse_sudarsana(chakras_soap)
    }

    return response
