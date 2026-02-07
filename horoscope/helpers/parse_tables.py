from horoscope.helpers.values import table_class_names, table_titles, etalon


def get_named_tables(tables):
    named_tables = {}

    for table in (
            table for table in tables.findAll("div", {"class": "table-natal"})
    ):
        current_table_classes = [
            css_class
            for css_class in table["class"]
            if css_class in table_class_names
        ]
        if len(current_table_classes):
            named_tables.update({current_table_classes[0]: table})
            if len(named_tables.keys()) == len(table_class_names):
                break

    return named_tables


def parse_tables(tables_html):
    # this find div exactly as specified string
    # tables = tables_html.find("div", {"class": "charts south north"})

    # this select divs that have "charts south north" classes at least
    tables = tables_html.select("div.charts.south.north")
    if len(tables) > 0:
        tables = tables[0]

    result = []
    named_table = get_named_tables(tables)

    for key in named_table.keys():
        table = named_table.get(key)
        data = []
        section_number = None

        for ns in table.findAll("div", {"class": "north-style"}):
            table_data = {
                "primaryData": [],
                "specialLagna": [],
                "upagraha": [],
                "grahaDrishti": [],
                "transsaturns": [],
                "mandyGulika": [],
                "arudhs": []
            }

            if "hidden" in ns["class"]:
                num = [cl for cl in ns["class"] if cl[:3] == "num"]
                if len(num):
                    section_number = num[0].split("-")[1]
                continue

            planets = []
            planets.extend([item for item in ns.findAll("span")])

            if not len(
                    [
                        planet.text.strip()
                        for planet in planets
                        if "hidden" not in planet["class"]
                    ]
            ):
                continue

            def get_formatted_planet(planet):
                return str([text for text in planet.strings][0]).strip()

            for planet in planets:
                if planet.text.strip() == "•":
                    continue

                if "primary-upagraha" in planet['class']:
                    table_data["mandyGulika"].append(get_formatted_planet(planet))
                    continue

                if "secondary-upagraha" in planet['class']:
                    table_data["transsaturns"].append(get_formatted_planet(planet))
                    continue

                if "special-lagna" in planet['class']:
                    table_data["specialLagna"].append(get_formatted_planet(planet))
                    continue

                if "arudha" in planet['class']:
                    table_data["arudhs"].append(get_formatted_planet(planet))
                    continue

                if "graha-drishti" in planet['class']:
                    table_data["grahaDrishti"].append(get_formatted_planet(planet))
                    continue

                if "transsaturn" in planet['class']:
                    table_data["transsaturns"].append(get_formatted_planet(planet))
                    continue

                if "p" in planet["class"]:
                    table_data["primaryData"].append(get_formatted_planet(planet))

            index = table.find(
                "div", {"class": f"north-style rasi rasi-{section_number}"}
            ).find("a").text

            data.append(
                {
                    "house": int(section_number),
                    "signId": int(index),
                    **table_data,
                }
            )

        if len(data) < 12:
            indexes = [
                i
                for i in list(
                    set(etalon) - set([int(i.get("signId")) for i in data])
                )
            ]
            for idx, i in enumerate(
                    list(set(etalon) - set([int(i.get("house")) for i in data]))
            ):
                data.append(
                    {
                        "house": int(i),
                        "signId": int(indexes[idx]),
                        "primaryData": [],
                        "specialLagna": [],
                        "upagraha": [],
                        "grahaDrishti": [],
                        "transsaturns": [],
                        "mandyGulika": [],
                        "arudhs": []
                    }
                )

        result.append(
            {
                "tableName": table_titles.get(key),
                "table": sorted(data, key=lambda table_item: table_item["house"]),
            }
        )

    return result
