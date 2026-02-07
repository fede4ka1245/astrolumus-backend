from django.conf import settings

table_class_names = [
    "rasi",
    "hora",
    "drekkana",
    "chaturthamsa",
    "panchamsa",
    "shashtamsa",
    "saptamsa",
    "ashtamsa",
    "navamsa",
    "dasamsa",
    "rudramsa",
    "dwadasamsa",
    "shodasamsa",
    "vimsamsa",
    "siddhamsa",
    "nakshatramsa",
    "trimsamsa",
    "khavedamsa",
    "akshavedamsa",
    "shashtiamsa",
    "navanavamsa",
    "ashtottaramsa",
    "nadiamsa",
]

table_titles = {
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
    "rudramsa": "D-11",
    "dwadasamsa": "D-12",
    "shodasamsa": "D-16",
    "vimsamsa": "D-20",
    "siddhamsa": "D-24",
    "nakshatramsa": "D-27",
    "trimsamsa": "D-30",
    "khavedamsa": "D-40",
    "akshavedamsa": "D-45",
    "shashtiamsa": "D-60",
    "navanavamsa": "D-81",
    "ashtottaramsa": "D-108",
    "nadiamsa": "D-150",
}


main_rashi_table_names = {
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

etalon = [i for i in range(1, 13)]

payload = {"user[login]": settings.J108_LOGIN, "user[password]": settings.J108_PASSWORD}
LOGIN_URL = "https://j108.ru/user"
