import requests
from bs4 import BeautifulSoup, Tag
from django.conf import settings
import urllib.parse

payload = {"user[login]": settings.J108_LOGIN, "user[password]": settings.J108_PASSWORD}
LOGIN_URL = "https://j108.ru/user"


def get_gochara_data(
    date_from,
    date_to,
    condition,
    planets,
    is_movement_merge,
    is_rasi_merge
):
    session = requests.Session()
    session.post(LOGIN_URL, data=payload)

    params = {
        "q[date_from]": date_from.strftime("%d.%m.%Y"),
        "q[date_to]": date_to.strftime("%d.%m.%Y"),
        "q[condition]": condition,
        "q[movement_type_merge]": 1 if is_movement_merge else '',
        "q[rasi_merge]": 1 if is_rasi_merge else '',
        "q[i][obj][]": [int(planet['planet']) for planet in planets],
        "q[i][pos][]": [planet['position'] for planet in planets],
        "q[i][chakra][]": ['rasi' for _ in planets],
        "q[i][mid][]": [planet['direction'] for planet in planets],
        "q[i][lon][]": [f"{planet['min']},{planet['max']}" for planet in planets],
    }

    url = "https://j108.ru/calendar/gochara/search?"
    data = session.get(url + urllib.parse.urlencode(params, True)).json()

    html = BeautifulSoup(data["html"])
    rows = html.find("table", {"class": "table table-striped"}).findChildren('tr')[1:-1]

    response = []

    for row in rows:
        signs = []
        date_start = ""
        date_end = ""

        for cell in row:
            if not(isinstance(cell, Tag)):
                continue

            if cell.get("class") is not None and "alcenter" in cell.get("class"):
                if cell.find('div', {"class": "ib"}) is None:
                    continue

                [sign, motion_type] = map(str, [s for s in cell.find('div', {"class": "ib"}).stripped_strings])

                signs.append({
                    'sign': sign if sign is not None else '',
                    'motionType': motion_type if motion_type is not None else ''
                })

                continue

            if date_start == "":
                date_start = cell.text.strip()
                continue

            date_end = cell.text.strip()

        response.append({
            "signs": signs,
            "dateStart": date_start,
            "dateEnd": date_end
        })

    return response
