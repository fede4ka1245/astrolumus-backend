## Конфигурация приложения

| Имя переменной                    | Тип  | Описание                                                                |
|-----------------------------------|------|-------------------------------------------------------------------------|
| DEBUG                             | bool | Включает или отключает режим отладки в Django                           |
| HEADLESS                          | bool | Определяет, работает ли приложение в режиме без графического интерфейса |
| APP_WORKERS                       | int  | Количество рабочих процессов в приложении                               |
| SECRET_KEY                        | str  | Секретный ключ Django для шифрования данных                             |
| ALLOWED_HOSTS                     | list | Список разрешённых хостов, с которых может обслуживаться Django         |
| CSRF_TRUSTED_ORIGINS              | list | Список доверенных источников для небезопасных запросов (например, POST) |
| DB_HOST                           | str  | Хост базы данных                                                        |
| DB_PORT                           | int  | Порт базы данных                                                        |
| DB_NAME                           | str  | Название базы данных                                                    |
| DB_USER                           | str  | Имя пользователя базы данных                                            |
| DB_PASSWORD                       | str  | Пароль пользователя базы данных                                         |
| PREVIEW_DB_HOST                   | str  | Хост базы данных сервиса ссылок                                         |
| PREVIEW_DB_PORT                   | int  | Порт базы данных сервиса ссылок                                         |
| PREVIEW_DB_NAME                   | str  | Название базы данных сервиса ссылок                                     |
| PREVIEW_DB_USER                   | str  | Имя пользователя базы данных сервиса ссылок                             |
| PREVIEW_DB_PASSWORD               | str  | Пароль пользователя базы данных сервиса ссылок                          |
| REDIS_URL                         | str  | URL-адрес подключения к Redis                                           |
| SMS_API_KEY                       | str  | API-ключ для отправки SMS                                               |
| SMS_ALPHA_NAME                    | str  | Имя отправителя SMS                                                     |
| DOMAIN                            | str  | Домен приложения                                                        |
| MINIO_ENDPOINT                    | str  | URL MinIO                                                               |
| MINIO_ACCESS_KEY                  | str  | Ключ доступа MinIO                                                      |
| MINIO_SECRET_KEY                  | str  | Секретный ключ MinIO                                                    |
| MINIO_PUBLIC_BUCKETS              | list | Список публичных бакетов MinIO                                          |
| MINIO_EXTERNAL_ENDPOINT           | str  | Внешний URL MinIO.                                                      |
| MINIO_EXTERNAL_ENDPOINT_USE_HTTPS | bool | Использовать ли HTTPS для взаимодействия с MinIO                        |
| BEPAID_SHOP_ID                    | str  | Идентификатор магазина BePaid                                           |
| BEPAID_SECRET_KEY                 | str  | Секретный ключ BePaid                                                   |
| J108_LOGIN                        | str  | Логин для сервиса J108                                                  |
| J108_PASSWORD                     | str  | Пароль для сервиса J108                                                 |
| YOOKASSA_ACCOUNT_ID               | str  | Идентификатор аккаунта YooKassa                                         |
| YOOKASSA_SECRET_KEY               | str  | Секретный ключ YooKassa                                                 |
| EMAIL_HOST                        | str  | SMTP-сервер для отправки почты                                          |
| EMAIL_HOST_USER                   | str  | Имя пользователя для SMTP                                               |
| EMAIL_HOST_PASSWORD               | str  | Пароль для SMTP                                                         |
| ADMINS                            | list | Список email-адресов администраторов и их имена                         |
| SENTRY_DSN                        | str  | DSN для интеграции с Sentry                                             |
| SENTRY_ENV                        | str  | Среда исполнения приложения для Sentry (например, production, staging)  |
| LOGURU_DIAGNOSE                   | bool | Включает режим детализированной диагностики в Loguru                    |
| SCHOOL_USER_ID                    | str  | Идентификатор пользователя аккаунта школы                               |
| FCM_PROJECT_ID                    | str  | Идентификатор проекта Firebase Cloud Messaging                          |
| FCM_PRIVATE_KEY_ID                | str  | Идентификатор приватного ключа Firebase                                 |
| FCM_PRIVATE_KEY                   | str  | Приватный ключ Firebase                                                 |
| FCM_CLIENT_EMAIL                  | str  | Email-адрес клиента Firebase                                            |
| FCM_CLIENT_ID                     | str  | Идентификатор клиента Firebase                                          |
| FCM_CLIENT_X509_CERT_URL          | str  | URL-адрес сертификата клиента Firebase                                  |
| DEFAULT_LANGUAGE_CODE             | str  | Языковой код переводов по умолчанию                                     |

## Деплоймент

Проект использует GitLab Runner с shell-executor. Скрипт развертывания описан в файле [gitlab-ci.yml](/.gitlab-ci.yml) и запускается автоматически при изменении ветки master/staging.

## Что делать если GitLab Runner не запускает job?

Иногда процесс GitLab Runner-a на сервере может зависнуть, в таком случае его нужно будет перезапустить.

`ssh <имя пользователя>@<ip-адрес сервера>`

Вводим пароль от пользователя

`sudo systemctl restart gitlab-runner` (Перезапускаем gitlab-runner)

`systemctl status gitlab-runner` (Проверяем его статус)

## Добавление новых секретов в приложение

Чтобы добавить новых секреты, нужно сперва их добавить в Settings → CI/CD → Variables.
Нажимаем 'Add Variable'. Далее вводим название и значение переменной.

Чтобы получить доступ к новому секрету в приложении нужно в [setup_env.sh](/.setup_env.sh) добавить запись этой переменной в .env таким образом:

`echo YOUR_VARIABLE_NAME=\"$YOUR_VARIABLE_NAME\"`

Новую переменную можно будет прочитать в django-приложении с помощью os:

```python3
import os

YOUR_VARIABLE_NAME = os.getenv("YOUR_VARIABLE_NAME")
```

## Как сделать резервную копию базы данных?

<!-- TODO: Реализовать автоматическое копирование -->

### 1. Подключаемся на сервер
```sh 
ssh <имя пользователя>@<ip-adress server>
```
Вводим пароль для пользователя сервера
### 2. Вводим команду для создания копии
```sh 
pg_dump -U your-db-user -F c -h 127.0.0.1 your-db-name > alpha-dump-name.sql
```

Вводим пароль от пользователя базы данных

### 3. (Optional) Копируем дамп с сервера на свою машину 
```sh 
scp <имя пользователя>@<ip-adress server>:/dump-path/alpha-dump-name.sql /local/path/on_your_machine
```

### 4. (Optional) Процесс восстановления данных из резервной копии

Удаляем существующий volume с базой данных
```sh 
docker volume rm your-volume-name
```

Копируем дамп в docker container
```sh 
docker cp alpha-dump-name.sql alpha-db-1:/
```

Восстанавливаем данные из дампа
```sh 
pg_restore -v --dbname=your-db-name --username=your-db-user --exit-on-error --no-owner --no-privileges --clean --if-exists --format=c --schema=public alpha-dump-name.sql
```
Далее вводим пароль от пользователя бд и всё готово.

## Как сделать резервную копию и восстановление MinIO с помощью `mc`?

### 1. Подключаемся к серверу MinIO

Добавляем MinIO в `mc` (если не добавлен):

```sh
mc alias set my-minio http://<minio-server>:9000 <access-key> <secret-key>
```

Проверяем подключение:

```sh
mc alias list
```

### 2. Создаём резервную копию MinIO

Список бакетов MinIO:

```sh
mc ls my-minio
```

Копируем данные из бакета MinIO в локальную папку:

```sh
mc cp -r my-minio/mybucket /backup/minio_backup
```

Или копируем все бакеты:

```sh
mc mirror my-minio /backup/minio_backup
```

### 3. (Optional) Процесс восстановления данных из резервной копии

Восстанавливаем данные обратно в MinIO:

```sh
mc mirror /backup/minio_backup my-minio
```

Или восстанавливаем отдельный бакет:

```sh
mc cp -r /backup/minio_backup/mybucket my-minio/mybucket
```


## Как лучше производить сложную миграцию на продуктовой базе данных?

### 1. Остановить django приложение

```shell
docker stop your-django-container-name
```

### 2. Сделать дамп продуктовой базы данных, загрузить его на свою машину и развернуть (см. описание выше)

### 3. Проверить применение миграции локально на дамп-е продуктовой базы

```sh 
docker exec -it your-django-container-name bash
python manage.py migrate
```

### 4. Если всё хорошо, можно вливать изменения в master ветку

Это запустит разворот приложения и миграцию базы данных (миграция - часть CI скрипта)

### 5. (Optional) Если локально миграция работает, а продуктовая база падает

Такого раньше замечено не было. Залейте дамп локально мигрированной базы данных на сервер и разверните его там
