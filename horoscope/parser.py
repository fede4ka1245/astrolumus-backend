import re
from operator import itemgetter

import requests
from bs4 import BeautifulSoup
from django.conf import settings

from horoscope.helpers.values import table_titles
from .helpers.parse_tables import parse_tables

payload = {"user[login]": settings.J108_LOGIN, "user[password]": settings.J108_PASSWORD}
LOGIN_URL = "https://j108.ru/user"


class Parser:
    def __init__(self, base_url):
        self.payload = payload
        self.base_url = base_url

    def get_proxy_data(self):
        with requests.Session() as s:
            s.post(LOGIN_URL, data=payload)

            r = s.get(self.base_url)
            return r.json()


    def get_ashtakavarga(self):
        url = f"{self.base_url}&fetch=ashtakavarga&data=dasa_system%3Dashtakavarga"

        with requests.Session() as s:
            s.post(LOGIN_URL, data=payload)
            r = s.get(url)

            soup = BeautifulSoup(r.json().get("html"))

            result = []

            table_names = []

            for charts_wrapper in soup.findAll("div", {"class": "charts-wrapper"}):
                chakra = charts_wrapper.find("div", {"class": "chakra"}).text.strip()

                data = []

                for wrapper in charts_wrapper.findAll("div", {"class": "north-style"}):
                    data.append(
                        {
                            "orderNumber": int(wrapper["class"][-1].split("-")[-1]),
                            "mainInfo": int(wrapper.text.strip()),
                            "isHighlighted": True
                            if wrapper.find("div", {"class": "bg _highlighted"})
                            else False,
                        }
                    )
                newlist = sorted(data, key=itemgetter("orderNumber"))

                if chakra not in table_names:
                    table_names.append(chakra)
                    result.append({"tableName": chakra, "table": newlist})

        return result

    def varshaphala_clean_data(self, element):
        a = element.find("a")
        if a:
            return " ".join([i.text.strip() for i in element.findAll("a")])
        else:
            return element.text.strip()

    def make_tajaka_yoga(self, td):
        div = td.find("div")
        span = td.find("span")

        if all([div, span]):
            return [
                div.text.strip().replace("\r\n", "").replace(" ", ""),
                span.text.strip().replace("\r\n", "").replace(" ", ""),
            ]
        else:
            return td.text.strip().replace("\r\n", "").replace(" ", "")

    def make_table_data(self, table_keys: dict, table_data: list) -> dict:
        data = []
        for i in table_data:
            if len(table_keys.keys()) == len(i):
                d = {}
                for n in range(0, len(i)):
                    d.update({table_keys.get(n): i[n]})
                data.append(d)
        return data

    def main_rashi_init(self, table_keys: dict, trs: list, tr_len=5) -> dict:
        table_data = {
            "primary-data": [],
            "special-lagna": [],
            "primary-upagraha": [],
            "secondary-upagraha": [],
            "transsaturn-data": [],
        }

        noClassTrs = []

        for tr in trs:
            if tr.get("class") is not None:
                if len(tr.get("class")) == 0:
                    if len(noClassTrs) < 19:
                        noClassTrs.append(tr)
                else:
                    if tr.get("class")[0] == "primary-data":
                        table_data["primary-data"].append(
                            [td for td in tr.findAll("td")[:tr_len]]
                        )

                    if tr.get("class")[0] == "transsaturn-data":
                        table_data["transsaturn-data"].append(
                            [td for td in tr.findAll("td")[:tr_len]]
                        )

        for tr in noClassTrs[:8]:
            table_data["special-lagna"].append([td for td in tr.findAll("td")[:tr_len]])

        for tr in noClassTrs[8:10]:
            table_data["primary-upagraha"].append(
                [td for td in tr.findAll("td")[:tr_len]]
            )

        for tr in noClassTrs[10:]:
            table_data["secondary-upagraha"].append(
                [td for td in tr.findAll("td")[:tr_len]]
            )

        return_data = {}
        for k in table_data.keys():
            return_data.update(
                {
                    "{}{}".format(
                        k.split("-")[0], k.split("-")[1].capitalize()
                    ): self.make_table_main_rashi_data(table_keys, table_data.get(k), k)
                }
            )
        return return_data

    def main_rashi_init_old(self, table_keys: dict, trs: list, tr_len=5) -> list:

        table_data = {}

        return_data = {}
        for tr in trs:
            if tr.get("class") is not None:
                data_type = (
                    tr.get("class")[0] if len(tr.get("class")) > 0 else "special-lagna"
                )

                if table_data.get(data_type):
                    table_data[data_type].append(
                        [td for td in tr.findAll("td")[:tr_len]]
                    )
                else:
                    table_data[data_type] = [[td for td in tr.findAll("td")[:tr_len]]]

        for k in table_data.keys():
            return_data.update(
                {
                    "{}{}".format(
                        k.split("-")[0], k.split("-")[1].capitalize()
                    ): self.make_table_main_rashi_data(table_keys, table_data.get(k), k)
                }
            )
        return return_data

    def make_table_main_rashi_data(
            self, table_keys: dict, table_data: list, data_type: str
    ) -> list:
        data = []

        for i in table_data:
            if len(table_keys.keys()) == len(i):
                d = {}
                for n in range(0, len(i)):
                    if table_keys.get(n) == "planet":
                        d.update(
                            {
                                table_keys.get(n): {
                                    "name": [
                                        i
                                        for i in i[n].text.split(" ")
                                        if len(i.strip())
                                    ][0].strip(),
                                    "isRetragraded": True
                                    if re.search(r"(R)", i[n].text.strip())
                                    else False,
                                    "additionalInfo": re.sub(
                                        r"\(R\)",
                                        "",
                                        i[n]
                                        .find("span", {"class": "qtip"})
                                        .text.strip(),
                                    )
                                    if i[n].find("span", {"class": "qtip"})
                                    else None,
                                }
                            }
                        )
                    elif table_keys.get(n) == "cpuxuta":
                        l = [i[n].find("span").text.strip()]
                        l.extend(
                            [
                                e.text.strip()
                                for e in i[n].find_all("div", {"class": "font-small"})
                            ]
                        )
                        d.update({table_keys.get(n): l})
                    elif table_keys.get(n) == "rashiNavamshi":

                        r = (
                            i[n]
                            .text.strip()
                            .replace("\r", "")
                            .replace("\n", "")
                            .split(" ")
                        )
                        d.update({"rashi": r[0], "namavashi": r[-1]})

                    elif table_keys.get(n) == "naksantra":
                        if re.search(r"-", i[n].text):
                            d.update(
                                {
                                    table_keys.get(n): {
                                        "mainInfo": i[n].text.strip(),
                                        "additionalInfo": None,
                                    }
                                }
                            )
                        else:
                            d.update(
                                {
                                    table_keys.get(n): {
                                        "mainInfo": i[n].find("a").text.strip(),
                                        "additionalInfo": i[n]
                                        .find("span")
                                        .text.strip(),
                                    }
                                }
                            )

                    elif table_keys.get(n) == "bhava":
                        d.update({table_keys.get(n): i[n].text.strip()})
                    else:
                        d.update({table_keys.get(n): i[n].text.strip()})
                data.append(d)
        return data

    def get_tajaka_yoga_data(self, table):

        tajaka_yoga_data = []

        table_keys = {
            0: "Солнце",
            1: "Луна",
            2: "Марс",
            3: "Меркурий",
            4: "Юпитер",
            5: "Венера",
            6: "Сатурн",
        }

        connection_types = {
            "badge-important": "important",
            "badge-info": "info",
            "badge-success": "success",
        }

        for tr in table.findAll("tr"):
            current_planet = None
            long_names = {
                'ИС': 'Итхасала-йога',
                'МС': 'Мутхасила-йога',
                'ЭР': 'Эсарапха-йога',
                'МР': 'Мусарипха-йога',
                'СА': 'Ямайа-йога',
                'СО': 'Накта-йога',
                'ЛУ': 'Камбула-йога'
            }
            for idx, x in enumerate(tr.findAll("td")):
                item = {}
                if idx == 0:
                    current_planet = x.text
                else:
                    if x.find("div"):
                        item.update(
                            {
                                "planets": [current_planet, table_keys.get((idx - 1))],
                                "connection": {
                                    "connection": x.find("div").text.strip(),
                                    "type": x.find("div")["class"][0],
                                },
                            }
                        )
                        tajaka_yoga_data.append(item)
                    if x.find("span"):
                        raw = x.find("span").text.strip().split(" ")
                        resize = (
                            x.find("span").find("i")["class"][0]
                            if x.find("span").find("i")
                            else None
                        )
                        item.update(
                            {
                                "badge": {
                                    "number": int(raw[0]) if len(raw) > 1 else None,
                                    "name": raw[-1],
                                    "fullName": long_names.get(raw[-1].upper()),
                                    "type": connection_types.get(
                                        [
                                            cl
                                            for cl in x.find("span")["class"]
                                            if cl[:6] == "badge-"
                                        ][0]
                                    ),
                                    "resize": resize,
                                }
                            }
                        )

        return tajaka_yoga_data

    def get_mudda_dasha_data(self, soup):
        res = []
        parent_divs = [
            i for i in soup.findAll("div", {"class": "dasa-container depth-0"})
        ]

        for first_div in parent_divs:
            data = {}

            w_140 = first_div.find("div", {"class": "w-140"}).text.strip().split(" ")
            planet = first_div.find("div", {"class": "name"}).text.strip()
            date_start = " ".join(w_140[:-1])
            time_start = w_140[-1]
            planets = [
                i
                for i in first_div.find("div", {"class": "supname"})
                .text.strip()
                .replace("\\", "")
                .split(" ")
                if len(i)
            ]

            end_div = (
                first_div.findAll("div", {"class": "ib"})[-1].text.strip().split(" ")
            )

            date_end = " ".join(end_div[:-1])
            time_end = end_div[-1]

            data.update(
                {
                    "planet": planet,
                    "date_start": date_start,
                    "time_start": time_start,
                    "date_end": date_end,
                    "time_end": time_end,
                    "planets": planets,
                    "subTable": [],
                }
            )

            for two_div in (
                    i for i in first_div.findAll("div", {"class": "dasa-container depth-1"})
            ):
                two_item = {}

                w_140 = two_div.find("div", {"class": "w-140"}).text.strip().split(" ")
                planet = two_div.find("div", {"class": "name"}).text.strip()
                date_start = " ".join(w_140[:-1])
                time_start = w_140[-1]

                end_div = (
                    two_div.findAll("div", {"class": "ib"})[-1].text.strip().split(" ")
                )

                date_end = " ".join(end_div[:-1])
                time_end = end_div[-1]
                planets = [
                    i
                    for i in two_div.find("div", {"class": "supname"})
                    .text.strip()
                    .replace("\\", "")
                    .split(" ")
                    if len(i)
                ]

                two_item.update(
                    {
                        "planet": planet,
                        "date_start": date_start,
                        "time_start": time_start,
                        "date_end": date_end,
                        "time_end": time_end,
                        "planets": planets,
                        "subTable": [],
                    }
                )

                data["subTable"].append(two_item)

                for three_div in (
                        i
                        for i in two_div.findAll("div", {"class": "dasa-container depth-2"})
                ):
                    three_item = {}

                    w_140 = (
                        three_div.find("div", {"class": "w-140"})
                        .text.strip()
                        .split(" ")
                    )
                    planet = three_div.find("div", {"class": "name"}).text.strip()
                    date_start = " ".join(w_140[:-1])
                    time_start = w_140[-1]

                    end_div = (
                        three_div.findAll("div", {"class": "ib"})[-1]
                        .text.strip()
                        .split(" ")
                    )

                    date_end = " ".join(end_div[:-1])
                    time_end = end_div[-1]
                    planets = [
                        i
                        for i in three_div.find("div", {"class": "supname"})
                        .text.strip()
                        .replace("\\", "")
                        .split(" ")
                        if len(i)
                    ]

                    three_item.update(
                        {
                            "planet": planet,
                            "date_start": date_start,
                            "time_start": time_start,
                            "date_end": date_end,
                            "time_end": time_end,
                            "planets": planets,
                            "subTable": [],
                        }
                    )
                    two_item["subTable"].append(three_item)

            res.append(data)
        return res

    def get_general_table_data(self):
        data = []

        table_names = {
            "rasi": "D-1",
            "hora": "D-2",
            "drekkana": "D-3",
            "chaturthamsa": "D-4",
            "panchamsa": "D-5",
            "shashtamsa": "D-6",
            "saptamsa": "D-7",
            "ashtamsa": "D-8",
            "navamsa": "D-9",
            "dasamsa": "D-10",
            "dwadasamsa": "D-12",
            "shodasamsa": "D-16",
            "siddhamsa": "D-24",
            "navanavamsa": "D-81",
        }

        with requests.Session() as s:
            s.post(LOGIN_URL, data=payload)

            for table_name in table_names.keys():
                r = s.get(f"{self.base_url}&chakra={table_name}&fetch=infotable")

                soup = BeautifulSoup(r.json().get("html"))

                table = soup.find("table")
                table_data = table.find_all("tr")

                keys_main_table = {
                    0: "planet",
                    1: "cpuxuta",
                    2: "rashiNavamshi",
                    3: "naksantra",
                }

                data.append(
                    {
                        "tableName": table_names.get(table_name),
                        "table": self.main_rashi_init(
                            keys_main_table, table_data, tr_len=4
                        ),
                    }
                )
            return data

    def get_varshaphala_charts(self, soup):
        return parse_tables(soup)

    def get_main_rashi_one_table_data(self, s, url, main_rashi_data, table_name):
        r = s.get(url)

        soup = BeautifulSoup(r.json().get("html"))

        table = soup.find("table")
        table_data = table.find_all("tr")

        keys_main_table = {
            0: "planet",
            1: "cpuxuta",
            2: "rashiNavamshi",
            3: "naksantra",
        }
        return {
            "tableName": table_titles.get(table_name),
            "table": self.main_rashi_init(keys_main_table, table_data, tr_len=4),
        }
        # main_rashi_data.append(
        #     {
        #         "tableName": table_name,
        #         "table": self.main_rashi_init(keys_main_table, table_data, tr_len=4),
        #     }
        # )

    def get_varshaphala_rasi_one_table_data(self, s, soup, main_rashi_data, table_name):
        # third table in returned HTML
        table = soup.find_all("table")[2]
        table_data = table.find_all("tr")

        keys_main_table = {
            0: "planet",
            1: "cpuxuta",
            2: "rashiNavamshi",
            3: "naksantra",
        }
        return {
            "tableName": table_titles.get(table_name),
            "table": self.main_rashi_init(keys_main_table, table_data, tr_len=4),
        }

    def get_varshaphala(self):
        url = f"{self.base_url}&month=&fetch=varshaphala"

        data = []

        res = {
            "main": [],
            "yogaTable": [],
            "dashiMap": [],
            "pvb": [],
            "horoscopeMaps": [],
            "rashiMap": [],
            "dt": None,
            "varshesha": None,
        }

        with requests.Session() as s:
            s.post(LOGIN_URL, data=payload)
            r = s.get(url)

            soup = BeautifulSoup(r.json().get("html"))

            tajaka_chart_div = soup.find("div", {"class": "tajaka-chart"})
            h3 = tajaka_chart_div.find("h3")

            res["dt"] = h3.text

            varshesha_div = soup.find("div", {"class": "varshesha"})
            sl5_elements = varshesha_div.find_all("div", {"class": "sl-5"})

            res["varshesha"] = " ".join(
                [
                    s.replace("\n", "")
                    for s in sl5_elements[1].text.split(" ")
                    if len(s.replace("\n", ""))
                ]
            )

            charts = self.get_varshaphala_charts(soup)

            div = soup.find("div", {"class": "tajaka-basic"})

            tables = div.findAll("table")

            table_count = 0

            keys_main_table_1 = {0: "point", 1: "graxa", 2: "pvb"}

            keys_main_table_2 = {
                0: "planet",
                1: "cpuxuta",
                2: "rashiNavamshi",
                3: "naksantra",
                4: "bhava",
            }

            keys_tajaka_yoga_table = {
                0: "planet",
                1: "sun",
                2: "moon",
                3: "mars",
                4: "mercury",
                5: "jupiter",
                6: "venus",
                7: "saturn",
            }

            for table in tables:
                table_count += 1

                length = 3 if table_count == 1 else 5
                table_data = []

                if table_count == 1:
                    for tr in table.findAll("tr"):
                        table_data.append(
                            [
                                self.varshaphala_clean_data(td)
                                if table_count == 1
                                else td
                                for td in tr.findAll("td")[:length]
                            ]
                        )
                else:
                    table_data = table.find_all("tr")

                if table_count == 1:
                    res["main"] = self.make_table_data(
                        keys_main_table_1 if table_count == 1 else keys_main_table_2,
                        table_data,
                    )

            div_tajaka_yoga = soup.find("div", {"class": "tajaka-yoga"})

            res["yogaTable"] = self.get_tajaka_yoga_data(div_tajaka_yoga)

            pvb_table = soup.find("div", {"class": "tajaka-bala-1"})

            keys_pvb_table = {0: "planet", 1: "total"}

            pvb_table_data = []
            for tr in pvb_table.findAll("tr"):
                tds = tr.findAll("td")
                if len(tds) >= 2:
                    pvb_table_data.append(
                        [
                            self.varshaphala_clean_data(tds[0]),
                            self.varshaphala_clean_data(tds[2]),
                        ]
                    )

            res["pvb"] = self.make_table_data(keys_pvb_table, pvb_table_data)
            # data.append(
            #    {
            #        "tableName": "pvb",
            #        "table": self.make_table_data(keys_pvb_table, pvb_table_data),
            #    }
            # )
            res["dashiMap"] = self.get_mudda_dasha_data(soup)
            # data.append(
            #    {"tableName": "mudda_dasha", "table": self.get_mudda_dasha_data(soup)}
            # )

            pvb_table = soup.find("div", {"class": "tajaka-bala-1"})

            keys_pvb_table = {0: "planet", 1: "total"}

            pvb_table_data = []
            for tr in pvb_table.findAll("tr"):
                tds = tr.findAll("td")
                if len(tds) >= 2:
                    pvb_table_data.append(
                        [
                            self.varshaphala_clean_data(tds[0]),
                            self.varshaphala_clean_data(tds[2]),
                        ]
                    )

            # data.append(
            #    {
            #        "tableName": "pvb",
            #        "table": self.make_table_data(keys_pvb_table, pvb_table_data),
            #    }
            # )

            div_varshesha = soup.find("div", {"class": "well well-small varshesha"})
            a_varshesha = div_varshesha.find("a", {"class": "font-large"})

            r = requests.get(f"https://j108.ru{a_varshesha['href']}")

            soup_varshesha = BeautifulSoup(r.text)

            h1 = soup_varshesha.find("h1", {"class": "h-fancy"})
            ul = soup_varshesha.find("ul")

            # data.append(
            #    {
            #        "ruler_year": a_varshesha.text,
            #        "text": [h1.text.strip(), ul.text.strip()],
            #    }
            # )
            res.update(
                {
                    "ruler_year": a_varshesha.text,
                    "text": [h1.text.strip(), ul.text.strip()],
                }
            )
        # data.extend(charts)

        # manager = multiprocessing.Manager()

        # main_rashi_data = manager.list()
        main_rashi_data = []

        # jobs = []

        # for table_name in table_titles.keys():
        #     t_url = f"{self.base_url}&chakra={table_name}&fetch=infotable"
        #     self.get_main_rashi_one_table_data(
        #         s, t_url, main_rashi_data, table_name
        #     )

        # t_url = f"{self.base_url}&chakra={table_name}&fetch=varshaphala"
        # main_rashi_data.append(
        #     self.get_varshaphala_rasi_one_table_data(
        #         s, t_url, main_rashi_data, table_name
        #     )
        # )
        #
        #     # p = multiprocessing.Process(
        #     #    target=self.get_main_rashi_one_table_data,
        #     #    args=(s, t_url, main_rashi_data, table_name),
        #     # )
        #     # jobs.append(p)
        #     # p.start()

        main_rashi_data.append(
            self.get_varshaphala_rasi_one_table_data(
                s, soup, main_rashi_data, "rasi"
            )
        )

        # for proc in jobs:
        #    proc.join()

        res["rashiMap"] = list(main_rashi_data)
        # data.append({"tableName": "main_rashi", "table": list(main_rashi_data)})
        res["horoscopeMaps"] = charts

        return res

    def clean_chakra_element(self, element):
        if element.find("span"):
            return [""]
        if len(str(element).split("<br/>")) > 1:
            return [
                       i.strip()
                       for i in " ".join(str(element).split("<br/>")).split(" ")
                       if len(i.strip())
                   ][1:3]
        return [element.text.strip()]
