from .get_dashi_item import get_dashi_item


def parse_dashi_table(dashiHTML):
    result = []

    first_rows = dashiHTML.css('.depth-0')

    for row1 in first_rows:
        item1 = get_dashi_item(row1)

        result.append(item1)

        second_rows = row1.css('.depth-1')

        for row2 in second_rows:
            item2 = get_dashi_item(row2)

            item1['subTable'].append(item2)

            third_rows = row2.css('.depth-2')

            for row3 in third_rows:
                item3 = get_dashi_item(row3)

                item2['subTable'].append(item3)

    return result
