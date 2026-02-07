import requests
from bs4 import BeautifulSoup
from django.conf import settings
from .helpers.parse_tables import parse_tables

payload = {"user[login]": settings.J108_LOGIN, "user[password]": settings.J108_PASSWORD}

LOGIN_URL = "https://j108.ru/user"


def name_maker_by_classes(classes: list, exclude_classes: list = []):
    return "_".join(list(filter(lambda x: x not in exclude_classes, classes)))


def get_tr_data(tr):
    data = []

    td_list = tr.findAll("td")

    for td in td_list:
        data.append(
            "".join(
                [item.text.strip() for item in td.children if len(item.text.strip())]
            )
        )
    return data


def get_data_table_tab(name_tub):
    pass


def get_data_in_table(html, tab_name):

    data = []

    soup = BeautifulSoup(html)

    if tab_name == "rasi":

        div = soup.find("div", {"class": "basic-info"})

        table = div.find("table", {"class": "table"})
    else:
        table = soup.find("table", {"class": "table"})

    tr_list = table.findAll("tr")

    for tr in tr_list[1:]:
        data.append(get_tr_data(tr))
    return data


def get_rectification_result(html):
    soup = BeautifulSoup(html)
    a = soup.find("a", {"class": "preview-trigger qtip"})
    # rectification_result = soup.find("div", {"id": "rectification-result"})
    return {}


def get_dashi_data(url, s):
    url_vim = f"{url}&fetch=dasa&data=dasa_system%3Dvmd"
    url_chr = f"{url}&fetch=dasa&data=dasa_system%3Dchd"

    res = {"vim": [], "chr": []}

    r = s.get(url_vim)
    soup = BeautifulSoup(r.json().get("html"))
    parent_divs = soup.findAll("div", {"class": "dasa-container"})

    for first_div in parent_divs:
        data = []
        data.append(
            [
                i.text.strip()
                for i in first_div.findAll("div", {"class": "ib"})
                if len(i.text.strip())
            ]
        )
        for two_div in first_div.findAll("div", {"class": "dasa-container"}):
            data.append(
                [
                    i.text.strip()
                    for i in two_div.findAll("div", {"class": "ib"})
                    if len(i.text.strip())
                ]
            )
            for three_div in two_div.findAll("div", {"class": "dasa-container"}):
                data.append(
                    [
                        i.text.strip()
                        for i in three_div.findAll("div", {"class": "ib"})
                        if len(i.text.strip())
                    ]
                )

        res["vim"].append(data)

    r = s.get(url_chr)
    soup = BeautifulSoup(r.json().get("html"))
    parent_divs = soup.findAll("div", {"class": "dasa-container"})

    for first_div in parent_divs:
        data = []
        data.append(
            [
                i.text.strip()
                for i in first_div.findAll("div", {"class": "ib"})
                if len(i.text.strip())
            ]
        )
        for two_div in first_div.findAll("div", {"class": "dasa-container"}):
            data.append(two_div.text.strip())
            for three_div in two_div.findAll("div", {"class": "dasa-container"}):
                data.append(three_div.text.strip())

        res["chr"].append(data)
    return res


def get_data(url: str) -> dict:
    session = requests.Session()

    session.post(LOGIN_URL, data=payload)
    maps_response = session.get(url)

    tables_html = BeautifulSoup(maps_response.text)

    return parse_tables(tables_html)