from bs4 import Tag


def parse_chakra(chackra_soap):
    result = []

    for cell in chackra_soap:
        if not (isinstance(cell, Tag)) or cell.text.strip().replace(' ', '') == '':
            continue

        cell_data = {
            'value': cell.text.strip(),
        }

        if cell.get('class') is not None:
            if 'unfavourable' in cell.get('class'):
                cell_data['color'] = 'red'
            elif 'semiunfavourable' in cell.get('class'):
                cell_data['color'] = 'yellow'
            else:
                 cell_data['color'] = 'green'

        if cell.get('title') is not None and cell.get('title') != '':
            [title, text] = cell.get('title').split('<br/>')

            cell_data['tip'] = {
                'title': title,
                'text': text
            }

        result.append(cell_data)

    return result