"""
Добавляет английские переводы и описания ко всем ключам в Tolgee.

Работает с namespace 'backend' (verbose_name, field labels, choices, fieldsets).
Для tariffs/content — проверяет наличие EN, добавляет где нет.
"""

import logging

from django.apps import apps
from django.core.management.base import BaseCommand

from utils.tolgee_client import (
    get_languages,
    upsert_keys_batch,
)

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Словарь общих переводов RU → EN
# -----------------------------------------------------------------------
COMMON_RU_EN = {
    # Django built-in
    "запись в журнале": "log entry",
    "записи в журнале": "log entries",
    "ID": "ID",
    "время действия": "action time",
    "пользователь": "user",
    "тип содержимого": "content type",
    "идентификатор объекта": "object ID",
    "представление объекта": "object representation",
    "тип действия": "action flag",
    "Добавление": "Addition",
    "Изменить": "Change",
    "Удаление": "Deletion",
    "сообщение об изменении": "change message",
    "право": "permission",
    "права": "permissions",
    "кодовое имя": "codename",
    "тип контента": "content type",
    "типы контента": "content types",
    "Python MIME тип": "Python MIME type",
    "модель": "model",
    "приложение": "application",
    "сессия": "session",
    "сессии": "sessions",
    "данные сессии": "session data",
    "дата окончания": "expiry date",
    "ключ сессии": "session key",
    "cron": "cron",
    "crontab": "crontab",
    "interval": "interval",
    "clocked": "clocked",
    "solar event": "solar event",
    "periodic task": "periodic task",
    "periodic tasks": "periodic tasks",

    # Общие поля
    "Название": "Title",
    "Описание": "Description",
    "Создан": "Created",
    "Создана": "Created",
    "Обновлен": "Updated",
    "Обновлена": "Updated",
    "Опубликован": "Published",
    "Статус": "Status",
    "Код": "Code",
    "Ссылка": "Link",
    "Фото": "Photo",
    "Фото превью": "Photo preview",
    "Фото оригинал": "Original photo",
    "Изображение": "Image",
    "Автор": "Author",
    "Категория": "Category",
    "Тип": "Type",
    "Имя": "Name",
    "Дата создания": "Created at",
    "Дата изменения": "Updated at",
    "Дата начала": "Start date",
    "Дата обновления": "Updated at",
    "Дата события": "Event date",
    "Дата рождения": "Date of birth",
    "Дата отмены": "Canceled at",
    "Псевдоним": "Alias",
    "Валюта": "Currency",
    "Пользователь": "User",
    "Тариф": "Tariff",
    "Заказ": "Order",
    "Баннер": "Banner",
    "Комментарий": "Comment",
    "Отправлено": "Sent",
    "Проверен": "Reviewed",

    # Users
    "Язык приложения": "Application language",
    "Языки приложения": "Application languages",
    "user": "user",
    "users": "users",
    "group": "group",
    "groups": "groups",
    "временный пароль": "temporary password",
    "временные пароли": "temporary passwords",
    "Файл пользователя": "User file",
    "Файлы пользователей": "User files",
    "Профиль пользователя": "User profile",
    "Профили пользователей": "User profiles",
    "Подписка": "Subscription",
    "Подписки": "Subscriptions",
    "Заблокированный пользователь": "Blocked user",
    "Заблокированные пользователи": "Blocked users",
    "Тип файла": "File type",
    "Фото": "Photo",
    "Сертификат": "Certificate",
    "Расскажите о себе": "Tell about yourself",
    "Показывать профиль полностью или сокращенно": "Show full or shortened profile",
    "Уведомления от пользователей": "User notifications",
    "Календарь": "Calendar",
    "Астро процессор": "Astro processor",
    "Форум": "Forum",
    "Роль пользователя": "User role",
    "Обычный пользователь": "Regular user",
    "Администратор школы": "School administrator",
    "Ожидает": "Awaiting",
    "Принят": "Accepted",
    "Отклонен": "Rejected",
    "Форум отключен": "Forum disabled",
    "Отключить форум пользователю": "Disable forum for user",
    "name": "name",
    "language code": "language code",
    "email address": "email address",
    "first name": "first name",
    "last name": "last name",
    "patronymic": "patronymic",
    "preferred UI language": "preferred UI language",
    "application language": "application language",

    # Tariffs
    "Семейство тарифов": "Tariff family",
    "Семейства тарифов": "Tariff families",
    "Тарифы": "Tariffs",
    "Активация тарифа": "Tariff activation",
    "Активации тарифов": "Tariff activations",
    "Платеж с сайта": "Website payment",
    "Платежи с сайта": "Website payments",
    "Публичный тариф": "Public tariff",
    "Отображается в списке карточек для перехода/и на сайте": "Displayed in the card list for navigation and on the website",
    "Для отображения пользователю как активированного тарифа": "Displayed to the user as an activated tariff",
    "Публичное описание": "Public description",
    "Для использования в карточках": "For use in cards",
    "При оплате тарифа из одного семейства срок активации, отсчитывается от последней не просроченной активации любого тарифа из семейства": "When paying for a tariff from the same family, the activation period starts from the last non-expired activation of any tariff from the family",
    "Действует с": "Valid from",
    "Действует по": "Valid until",
    "Срок действия после активации, дней": "Validity after activation, days",
    "Если 0 - действует бессрочно": "If 0 — valid indefinitely",
    "Приоритет для тарифа по умолчанию": "Priority for default tariff",
    "Тариф по умолчанию, выбирается как действующий на текущую дату и имеющий наивысший приоритете среди прочих. Применяется для новых пользователей": "Default tariff, selected as active on the current date with the highest priority among others. Applied to new users",
    "Может работать параллельно с другими тарифами": "Can work in parallel with other tariffs",
    "Параметр не обрабатывается, оставлен на будущее": "Parameter not processed, left for future use",
    "Астропроцессор отключен": "Astroprocessor disabled",
    "Ограничить количество тем": "Limit number of topics",
    "Ограничить количество гороскопов": "Limit number of horoscopes",
    "Срок действия астропроцессора после активации, дней": "Astroprocessor validity after activation, days",
    "Тариф для перехода после окончания всех других тарифов": "Tariff to switch to after all other tariffs expire",
    "Ссылка на тариф": "Tariff link",
    "Цена (RUB)": "Price (RUB)",
    "Цена в российских рублях": "Price in Russian rubles",
    "Цена (BYN)": "Price (BYN)",
    "Цена в белорусских рублях": "Price in Belarusian rubles",
    "Цена (USD)": "Price (USD)",
    "Цена в американских долларах": "Price in US dollars",
    "Цена (EUR)": "Price (EUR)",
    "Цена в евро": "Price in euros",
    "Сумма платежа": "Payment amount",
    "рубль": "ruble",
    "белорусский рубль": "Belarusian ruble",

    # Astroprocessor
    "Тип данных астропроцессора": "Astroprocessor data type",
    "Данные астропроцессора": "Astroprocessor data",
    "Планета в знаке": "Planet in sign",
    "Планеты в знаке": "Planets in sign",
    "Планета в доме": "Planet in house",
    "Планеты в доме": "Planets in house",
    "Управитель": "Ruler",
    "Знак Зодиака": "Zodiac sign",
    "Знаки Зодиака": "Zodiac signs",
    "Накшатра": "Nakshatra",
    "Накшатры": "Nakshatras",
    "Планета / лагна / упаграха": "Planet / lagna / upagraha",
    "Планеты, дополнительные лагны, упаграхи": "Planets, additional lagnas, upagrahas",
    "Карака": "Karaka",
    "Караки": "Karakas",
    "Арудха": "Arudha",
    "Арудхи": "Arudhas",
    "Дом": "House",
    "Дома": "Houses",
    "Планета в знаке (данные)": "Planet in sign (data)",
    "Дом (тип)": "House (type)",
    "Внутренний id": "Internal ID",
    "Публичная запись": "Public record",
    "Планета": "Planet",
    "Знак": "Sign",
    "Управитель дома": "House ruler",
    "В доме": "In house",

    # Info
    "Информация": "Information",
    "Документ": "Document",
    "Документы": "Documents",
    "Мобильная версия": "Mobile version",
    "Мобильные версии": "Mobile versions",
    "Информация о разделе приложения": "App section information",
    "Код документа": "Document code",
    "Код для отличия документа (например, privacy)": "Code to distinguish document (e.g., privacy)",
    "Содержимое": "Content",
    "Используется последняя опубликованная редакция": "The latest published version is used",
    "Код раздела приложения": "App section code",
    "Код для раздела приложения (например, scholar)": "Code for app section (e.g., scholar)",
    "Подзаголовок": "Subtitle",
    "Главное описание": "Main description",
    "Активный раздел": "Active section",
    "версия": "version",
    "android": "android",
    "ios": "ios",

    # Horoscope
    "Гороскоп": "Horoscope",
    "Гороскопы": "Horoscopes",
    "Мой гороскоп": "My horoscope",
    "Мои гороскопы": "My horoscopes",
    "Полный гороскоп": "Full horoscope",
    "Полные гороскопы": "Full horoscopes",

    # Bootcamp
    "Курс": "Course",
    "Курсы": "Courses",
    "Дополнительное поле": "Additional field",
    "Дополнительные поля": "Additional fields",
    "Видео презентация": "Video presentation",
    "Видео презентации": "Video presentations",
    "Для кого курс": "Who the course is for",
    "Для кого курсы": "Who the courses are for",
    "В рамках курса": "Within the course",
    "В рамках курсов": "Within the courses",
    "Что вы покупаете": "What you buy",
    "Тип варианта оплаты": "Payment option type",
    "Типы вариантов оплаты": "Payment option types",
    "Вариант оплаты": "Payment option",
    "Варианты оплат": "Payment options",
    "Остались вопросы?": "Still have questions?",
    "Почему наши ученики элита Астрологии?": "Why are our students the elite of Astrology?",
    "Модуль": "Module",
    "Модули": "Modules",
    "Урок": "Lesson",
    "Уроки": "Lessons",
    "Учебный план": "Curriculum",
    "Учебные планы": "Curricula",
    "Бонус": "Bonus",
    "Бонусы": "Bonuses",
    "Тег для курсов": "Course tag",
    "Теги для курсов": "Course tags",
    "Особенность курсов": "Course feature",
    "Особенности курсов": "Course features",
    "Карточка рекламы курса": "Course ad card",
    "Карточки рекламы курсов": "Course ad cards",
    "Название курса": "Course title",
    "Тип курса": "Course type",
    "Название ступени": "Stage name",
    "Записаться на курс": "Enroll in course",
    "Продолжительность": "Duration",
    "Именной сертификат": "Personal certificate",
    "Почему наши ученики элита": "Why our students are the elite",
    "Стать участником курса": "Become a course member",
    "Получить консультацию": "Get a consultation",
    "Ступень": "Stage",
    "Дополнительный": "Additional",
    "Мастер класс": "Master class",
    "Мини": "Mini",
    "Ссылка на видео": "Video link",
    "Описание цены": "Price description",
    "Полная стоимость": "Full price",
    "Цена со скидкой": "Discounted price",
    "Написать в школу": "Write to the school",
    "Название модуля": "Module title",
    "Название урока": "Lesson title",
    "Цена": "Price",
    "Предыдущая цена": "Previous price",
    "Ссылка курс на сайте": "Course link on website",

    # Advertising
    "Раздел баннера": "Banner section",
    "Разделы баннеров": "Banner sections",
    "Тег для баннеров": "Banner tag",
    "Теги для баннеров": "Banner tags",
    "Изображение для баннеров": "Image for banners",
    "Изображения для баннеров": "Images for banners",
    "Баннеры": "Banners",

    # Forum
    "Категории": "Categories",
    "Фото топика": "Topic photo",
    "Фото топиков": "Topic photos",
    "Топик": "Topic",
    "Топики": "Topics",
    "Участник топика": "Topic member",
    "Участники топиков": "Topic members",
    "Комментарии": "Comments",
    "Последний прочитанный комментарий": "Last read comment",
    "Последние прочитанные комментарии": "Last read comments",
    "Правила форума": "Forum rules",
    "Название топика": "Topic title",
    "Дата публикации, при отсутствии даты, топик не показывается": "Publication date; if absent, the topic is not shown",
    "Дата проверки топика модератором": "Date of moderation review",
    "Комментарий модератора": "Moderator comment",
    "Уровень доступа": "Access level",
    "Ссылка на гороскоп": "Horoscope link",
    "Приватный": "Private",
    "Публичный": "Public",
    "Не проверена": "Not reviewed",
    "Допущена": "Approved",
    "В архиве": "Archived",
    "Заблокирована": "Blocked",
    "Временно заблокирована": "Temporarily blocked",
    "Статус автора темы": "Topic author status",
    "Статус приглашенного пользователя": "Invited user status",
    "Приглашен": "Invited",
    "Принял": "Accepted",
    "Отклонил": "Declined",
    "Текст комментария": "Comment text",
    "Родительский комментарий": "Parent comment",
    "Ждет проверки": "Awaiting review",
    "Допущен": "Approved",
    "Заблокирован": "Blocked",
    "Название правил": "Rules title",

    # Complaints
    "Жалоба": "Complaint",
    "Жалобы": "Complaints",
    "Ответ на жалобу": "Complaint response",
    "Ответы на жалобы": "Complaint responses",
    "Текст жалобы": "Complaint text",
    "На рассмотрении": "Under review",
    "Разрешена": "Resolved",
    "Отклонена": "Rejected",

    # Payments
    "Настройка платежей": "Payment settings",
    "Настройки платежей": "Payment settings",
    "Заказы": "Orders",
    "Запись об оплате": "Payment record",
    "Записи об оплатах": "Payment records",
    "Рекурентная подписка": "Recurring subscription",
    "Рекурентные подписки": "Recurring subscriptions",
    "Платформа": "Platform",
    "Платформа для которой настраиваются платежи": "Platform for which payments are configured",
    "Платежи включены": "Payments enabled",
    "Включить или выключить платежи для данной платформы": "Enable or disable payments for this platform",
    "сумма": "amount",
    "Платежные системы": "Payment systems",
    "Имя в приложении": "Name in app",
    "Фамилия в приложении": "Last name in app",
    "Email в приложении": "Email in app",
    "Имя при оплате": "Name at payment",
    "Фамилия при оплате": "Last name at payment",
    "Email при оплате": "Email at payment",
    "Название тарифа": "Tariff name",
    "Платежная система": "Payment system",
    "Сумма оплаты": "Payment amount",
    "Рекурентный платеж": "Recurring payment",
    "Является ли этот платеж частью рекурентной подписки": "Whether this payment is part of a recurring subscription",
    "ID платежа": "Payment ID",
    "Сырые данные платежа": "Raw payment data",
    "ID подписки": "Subscription ID",
    "ID клиента": "Customer ID",
    "Статус подписки": "Subscription status",
    "Сумма подписки": "Subscription amount",
    "Начало текущего периода": "Current period start",
    "Конец текущего периода": "Current period end",
    "Отменить в конце периода": "Cancel at period end",
    "Метаданные": "Metadata",
    "Успешно": "Successful",
    "Неуспешно": "Failed",
    "Ожидание": "Pending",
    "Активна": "Active",
    "Отменена": "Canceled",
    "Просрочена": "Past due",
    "Не оплачена": "Unpaid",
    "Пробный период": "Trial",
    "Не завершена": "Incomplete",
    "Не завершена (истекла)": "Incomplete (expired)",
    "Currency code (USD, RUB, BYN, EUR)": "Currency code (USD, RUB, BYN, EUR)",

    # Deep Sky
    "Созвездие": "Constellation",
    "Созвездия": "Constellations",
    "Тип звездного объекта": "Stellar object type",
    "Типы звездных объектов": "Stellar object types",
    "Объект": "Object",
    "Объекты": "Objects",
    "Год": "Year",
    "Года": "Years",
    "Область": "Area",
    "Тропический знак": "Tropical sign",
    "Сидерический знак": "Sidereal sign",
    "Дева": "Virgo",
    "Весы": "Libra",
    "Скорпион": "Scorpio",
    "Стрелец": "Sagittarius",
    "Козерог": "Capricorn",
    "Водолей": "Aquarius",
    "Рыбы": "Pisces",
    "Овен": "Aries",
    "Телец": "Taurus",
    "Близнецы": "Gemini",
    "Рак": "Cancer",
    "Лев": "Leo",
    "Тропический": "Tropical",
    "Сидерический": "Sidereal",

    # Notifications
    "Страница уведомления": "Notification page",
    "Страницы уведомлений": "Notification pages",
    "Раздел страниц уведомлений": "Notification pages section",
    "Разделы страниц уведомлений": "Notification pages sections",
    "Тег для страниц уведомлений": "Notification pages tag",
    "Теги для страниц уведомлений": "Notification pages tags",
    "Группа страниц уведомлений": "Notification page group",
    "Группы страниц уведомлений": "Notification page groups",
    "Задача на отправку уведомления": "Notification send task",
    "Задачи на отправку уведомлений": "Notification send tasks",
    "Заголовок": "Title",
    "Главная информация": "Primary information",
    "Второстепенная информация": "Secondary information",
    "Язык": "Language",
    "Главный баннер": "Primary banner",
    "Второстепенный баннер": "Secondary banner",
    "Название интересного тега": "Interesting tag title",
    "Интересный текст": "Interesting text",
    "Текст первой кнопки": "First button text",
    "Ссылка первой кнопки": "First button link",
    "Текст второй кнопки": "Second button text",
    "Ссылка второй кнопки": "Second button link",
    "Ссылка на ресурс": "Resource link",
    "Ссылка на видео": "Video link",
    "Доступна с": "Available from",

    # Calendar
    "Событие": "Event",
    "События": "Events",
    "Название события": "Event title",
    "Тип доступа": "Access type",
    "Частный": "Private",

    # Misc
    "избранное": "favorites",
    "автор": "author",
    "дата и время создания": "date and time of creation",
    "link": "link",
    "Стоп слово": "Stop word",
    "Стоп слова": "Stop words",

    # Admin fieldsets
    "Основная информация": "Basic information",
    "Пользователь в приложении": "User in app",
    "Данные при оплате (merchant)": "Payment data (merchant)",
    "Связанные объекты": "Related objects",
    "Сырые данные": "Raw data",
    "Финансовая информация": "Financial information",
    "Периоды подписки": "Subscription periods",
    "Даты": "Dates",
    "Personal info": "Personal info",
    "Translation": "Translation",
    "Permissions": "Permissions",
    "Important dates": "Important dates",

    # Admin display
    "Нет изображения": "No image",
    "Image": "Image",
    "About": "About",
    "отправить на один email, если указано": "send to a single email, if specified",
}


def _generate_description(key: str) -> str:
    """Генерирует описание ключа на основе его структуры."""
    parts = key.split(".")

    if len(parts) >= 3 and parts[-1] == "verbose_name":
        return f"Display name for model {parts[0]}.{parts[1]}"
    if len(parts) >= 3 and parts[-1] == "verbose_name_plural":
        return f"Plural display name for model {parts[0]}.{parts[1]}"
    if len(parts) >= 4 and parts[2] == "field":
        field_name = parts[3]
        if len(parts) >= 5 and parts[4] == "help_text":
            return f"Help text for field {parts[0]}.{parts[1]}.{field_name}"
        return f"Field label: {parts[0]}.{parts[1]}.{field_name}"
    if len(parts) >= 4 and parts[2] == "choice":
        return f"Choice label for {parts[0]}.{parts[1]}.{parts[3]}"
    if len(parts) >= 4 and parts[2] == "fieldset":
        return f"Admin fieldset title in {parts[0]}.{parts[1]}"
    if "admin" in parts:
        return f"Admin display label in {parts[0]}"

    # Dynamic content keys: model.pk.field
    if len(parts) == 3:
        try:
            int(parts[1])
            return f"Content field '{parts[2]}' for {parts[0]} (pk={parts[1]})"
        except ValueError:
            pass

    return f"Translation key: {key}"


class Command(BaseCommand):
    help = "Добавляет EN переводы и описания ко всем ключам в Tolgee"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--namespace", default=None,
            help="Обработать только указанный namespace",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        target_ns = options["namespace"]

        namespaces = ["backend", "tariffs", "content"]
        if target_ns:
            namespaces = [target_ns]

        for namespace in namespaces:
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(f"Namespace: {namespace}")
            self.stdout.write(f"{'='*60}")
            self._process_namespace(namespace, dry_run)

    def _process_namespace(self, namespace, dry_run):
        from utils.tolgee_client import _project_url, _headers
        import requests

        url = _project_url("/translations")
        page = 0
        keys_to_update = {}  # key_name → {"en": text}
        descriptions = {}     # key_name → description

        while True:
            params = {
                "filterNamespace": namespace,
                "languages": "ru,en",
                "size": 250,
                "page": page,
            }
            resp = requests.get(url, headers=_headers(), params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            embedded = data.get("_embedded", {})
            keys = embedded.get("keys", [])
            if not keys:
                break

            for key_entry in keys:
                key_name = key_entry.get("keyName", "")
                translations = key_entry.get("translations", {})

                ru_data = translations.get("ru", {})
                en_data = translations.get("en", {})
                ru_text = ru_data.get("text") if ru_data else None
                en_text = en_data.get("text") if en_data else None

                # Generate description
                descriptions[key_name] = _generate_description(key_name)

                # Add EN translation if missing
                if ru_text and not en_text:
                    en_translation = COMMON_RU_EN.get(ru_text)
                    if en_translation:
                        keys_to_update[key_name] = {"en": en_translation}
                    else:
                        # For untranslated keys, use the Russian text as-is
                        # (better than nothing, translator can fix in Tolgee UI)
                        keys_to_update[key_name] = {"en": ru_text}

            page_meta = data.get("page", {})
            total_pages = page_meta.get("totalPages", 1)
            page += 1
            if page >= total_pages:
                break

        translated_count = sum(
            1 for k, v in keys_to_update.items()
            if v["en"] != COMMON_RU_EN.get("") and v["en"] in COMMON_RU_EN.values()
        )
        self.stdout.write(f"  Ключей без EN перевода: {len(keys_to_update)}")
        self.stdout.write(f"  Из них с найденным переводом: {translated_count}")
        self.stdout.write(f"  Описаний для добавления: {len(descriptions)}")

        if dry_run:
            for key, trans in list(keys_to_update.items())[:15]:
                self.stdout.write(f"  {key}: {trans['en'][:60]}")
            return

        # Upload EN translations
        if keys_to_update:
            self.stdout.write(f"  Загрузка EN переводов...")
            from utils.tolgee_client import upsert_keys_batch
            result = upsert_keys_batch(namespace, keys_to_update)
            self.stdout.write(f"  EN переводы: {result['total_keys']} ключей")

        # Upload descriptions via API
        if descriptions:
            self.stdout.write(f"  Загрузка описаний...")
            self._upload_descriptions(namespace, descriptions)
            self.stdout.write(f"  Описания: {len(descriptions)} ключей")

    def _upload_descriptions(self, namespace, descriptions):
        """Update key descriptions via Tolgee API."""
        import time
        from utils.tolgee_client import _project_url, _headers
        import requests

        url = _project_url("/translations")
        page = 0
        updated = 0
        errors = 0

        while True:
            time.sleep(2)  # Rate limit protection
            params = {
                "filterNamespace": namespace,
                "size": 100,
                "page": page,
            }
            try:
                resp = requests.get(url, headers=_headers(), params=params, timeout=30)
                if not resp.ok:
                    self.stderr.write(f"  GET page {page} failed: {resp.status_code}")
                    break
                data = resp.json()
            except Exception as e:
                self.stderr.write(f"  GET page {page} error: {e}")
                break

            embedded = data.get("_embedded", {})
            keys = embedded.get("keys", [])
            if not keys:
                break

            for key_entry in keys:
                key_name = key_entry.get("keyName", "")
                key_id = key_entry.get("keyId")
                description = descriptions.get(key_name)

                if key_id and description:
                    update_url = _project_url(f"/keys/{key_id}")
                    try:
                        r = requests.put(
                            update_url,
                            headers=_headers(),
                            json={"name": key_name, "description": description},
                            timeout=10,
                        )
                        if r.ok:
                            updated += 1
                        else:
                            errors += 1
                    except Exception:
                        errors += 1

            page_meta = data.get("page", {})
            total_pages = page_meta.get("totalPages", 1)
            page += 1
            if page >= total_pages:
                break

            if page % 5 == 0:
                self.stdout.write(f"    ... page {page}/{total_pages}, updated {updated}")

        self.stdout.write(f"  Описания: обновлено {updated}, ошибок {errors}")
