def parse_sudarsana(chakras_soap):
    circle_lg_data = []
    circle_ch_data = []
    circle_sy_data = []
    box_sudarsana = chakras_soap.find("div", {"class": "box-sudarsana"})

    circle_lg = box_sudarsana.find("div", {"class": "circle-lg"})
    circle_ch = box_sudarsana.find("div", {"class": "circle-ch"})
    circle_sy = box_sudarsana.find("div", {"class": "circle-sy"})

    for i in range(1, 13):
        lg_rs_el = circle_lg.find("div", {"class": f"rs-{i}"})
        lg_bh_el = circle_lg.find("div", {"class": f"bh-{i}"})

        ch_rs_el = circle_ch.find("div", {"class": f"rs-{i}"})
        ch_bh_el = circle_ch.find("div", {"class": f"bh-{i}"})

        sy_rs_el = circle_sy.find("div", {"class": f"rs-{i}"})
        sy_bh_el = circle_sy.find("div", {"class": f"bh-{i}"})

        circle_lg_data.append(
            {
                "rs": {"value": lg_rs_el.text, "title": lg_rs_el["title"]},
                "bh": [
                    {"value": ib.text, "title": ib["title"]}
                    for ib in lg_bh_el.find_all("div", {"class": "ib"})
                ],
            }
        )
        circle_ch_data.append(
            {
                "rs": {"value": ch_rs_el.text, "title": ch_rs_el["title"]},
                "bh": [
                    {"value": ib.text, "title": ib["title"]}
                    for ib in ch_bh_el.find_all("div", {"class": "ib"})
                ],
            }
        )
        circle_sy_data.append(
            {
                "rs": {"value": sy_rs_el.text, "title": sy_rs_el["title"]},
                "bh": [
                    {"value": ib.text, "title": ib["title"]}
                    for ib in sy_bh_el.find_all("div", {"class": "ib"})
                ],
            }
        )

    return {
        "circleLg": circle_lg_data,
        "circleCh": circle_ch_data,
        "circleSy": circle_sy_data
    }
