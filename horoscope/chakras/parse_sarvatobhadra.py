from bs4 import Tag


def parse_sarvatobhadra(sarvatobhadra_children):
    result = []

    for cell in sarvatobhadra_children:
        if not (isinstance(cell, Tag)):
            continue

        cell_data = {
            'cellName': cell.get('data-index'),
            'elements': [],
            'grahas': []
        }

        for child in cell.findChildren('div'):
            if not (isinstance(child, Tag)) or child.text.strip().replace(' ', '') == '':
                continue

            if child.get('class') is not None and child.get('class')[0] == 'graha-container':
                graha = {'color': child.find('span').get('class')[0], 'name': child.text.strip()}

                cell_data['grahas'].append(graha)

                continue

            if child.name == 'div':
                cell_data['elements'].append(child.text.strip())

        result.append(cell_data)

    return result
