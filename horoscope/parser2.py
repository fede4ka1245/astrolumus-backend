from django.conf import settings
from selenium import webdriver
from selenium.common.exceptions import (
    ElementNotInteractableException,
    NoSuchElementException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

import geckodriver_autoinstaller

geckodriver_autoinstaller.install()


def name_maker_by_classes(classes: list, exclude_classes: list = []):
    return "_".join(list(filter(lambda x: x not in exclude_classes, classes)))


login = settings.J108_LOGIN
password = settings.J108_PASSWORD

login_url = "https://j108.ru/user"


pages = [
    "D-1",
    "D-2",
    "D-3",
    "D-4",
    "D-5",
    "D-6",
    "D-7",
    "D-8",
    "D-9",
    "D-10",
    "D-11",
    "D-12",
    "D-16",
    "D-20",
    "D-24",
    "D-27",
    "D-30",
    "D-40",
    "D-45",
    "D-60",
    "D-81",
    "D-108",
    "D-150",
]


def get_page_data(params: list, page_name: str) -> dict:
    result = {}

    for param in params:
        name_param = name_maker_by_classes(param.get_attribute("class").split(" "), [])
        value = [
            el.text for el in param.find_elements(By.TAG_NAME, "span") if len(el.text)
        ]
        data = {name_param: value}
        if result.get(name_param):
            new_value = result.get(name_param) + value
            result[name_param] = new_value
            return result
        else:
            result.update({name_param: value})

        return {page_name: result}


def run(url):
    firefox_options = webdriver.FirefoxOptions()
    if settings.HEADLESS:
        firefox_options.add_argument("--headless")
    browser = webdriver.Firefox(options=firefox_options)

    browser.get(login_url)
    browser.find_element(By.NAME, "user[login]").send_keys(login)
    browser.find_element(By.NAME, "user[password]").send_keys(password)

    controls = browser.find_element(By.CLASS_NAME, "controls")
    btns = browser.find_elements(By.TAG_NAME, "button")
    for btn in btns:
        if btn.text == "Войти":
            btn.click()
            break

    import time

    time.sleep(3)

    browser.get(url)
    time.sleep(3)

    result = {}

    for page in pages[:3]:

        chakras = browser.find_elements(By.CLASS_NAME, "chakra")

        for chakra in chakras:
            try:
                chakra_link = chakra.find_element(By.TAG_NAME, "a")
                chakra_link.click()
                time.sleep(1)
                break
            except (NoSuchElementException, ElementNotInteractableException):
                pass

        chart_list = browser.find_element(By.CLASS_NAME, "chart-list")
        for a in chart_list.find_elements(By.TAG_NAME, "a"):
            if a.text == page:
                a.click()
                time.sleep(1)

        chart = browser.find_element(By.CLASS_NAME, "charts")
        params = chart.find_elements(By.CLASS_NAME, "north-style")

        time.sleep(1)

    browser.close()
    return result
