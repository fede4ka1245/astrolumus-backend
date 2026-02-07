from datetime import datetime

months = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']


def format_date(date):
    if len(date.split(' ')) != 3:
        return date

    [day, month, year] = date.split(' ')

    return datetime.strptime(f"{day}/{months.index(month.lower()) + 1}/{year}", '%d/%m/%Y').strftime('%d/%m/%Y')