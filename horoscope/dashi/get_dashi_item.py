from horoscope.dashi.format_date import format_date


def get_dashi_item(rootNode):
    item = {}

    w_140 = rootNode.css_first(".w-140").text().strip().split(" ")
    planet = rootNode.css_first(".name").text()
    date_start = format_date(" ".join(w_140[:-1]))
    time_start = w_140[-1]

    end_div = rootNode.css(".ib")[-1].text().strip().split(" ")

    date_end = format_date(" ".join(end_div[:-1]))
    time_end = end_div[-1]
    planets = [planet for planet in rootNode.css_first(".supname").text().replace("\\", "").split(" ") if len(planet)]

    item.update(
        {
            "planet": planet,
            "dateStart": date_start,
            "timeStart": time_start,
            "dateEnd": date_end,
            "timeEnd": time_end,
            "planets": planets,
            "subTable": [],
        }
    )

    return item
