"""
Загрузчик переводов из S3 (MinIO).

Кеширует JSON файлы в памяти. Перезагружается по таймеру или вручную.
Используется API сериализаторами для получения локализованных значений
из Tolgee (через S3) вместо JSON-полей в БД.
"""

import json
import logging
import threading
import time
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)

_cache = {}  # {(namespace, lang): {key: value}}
_cache_lock = threading.Lock()
_cache_timestamp = 0.0
_CACHE_TTL = 300  # 5 minutes, matches Celery Beat schedule


def _get_minio_client():
    from minio import Minio

    return Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_USE_HTTPS,
    )


def _load_from_s3(namespace: str, lang: str) -> dict:
    """Загружает JSON файл переводов из S3."""
    prefix = settings.TOLGEE_TRANSLATIONS_S3_PREFIX
    path = f"{prefix}/{namespace}/{lang}.json"
    bucket = "alpha"

    try:
        client = _get_minio_client()
        response = client.get_object(bucket, path)
        data = json.loads(response.read().decode("utf-8"))
        response.close()
        response.release_conn()
        return data
    except Exception as e:
        logger.debug("Failed to load translations %s/%s from S3: %s", namespace, lang, e)
        return {}


def _ensure_cache_fresh():
    """Перезагружает кеш если TTL истёк."""
    global _cache_timestamp
    now = time.time()
    if now - _cache_timestamp < _CACHE_TTL:
        return

    with _cache_lock:
        # Double-check after acquiring lock
        if now - _cache_timestamp < _CACHE_TTL:
            return
        _cache_timestamp = now
        # Cache is lazy — entries are loaded on demand, but we clear stale ones
        _cache.clear()


def get_translations(namespace: str, lang: str) -> dict:
    """
    Возвращает dict переводов для namespace+lang.
    Кеширует в памяти.
    """
    _ensure_cache_fresh()
    cache_key = (namespace, lang)

    if cache_key not in _cache:
        with _cache_lock:
            if cache_key not in _cache:
                _cache[cache_key] = _load_from_s3(namespace, lang)

    return _cache.get(cache_key, {})


def get_translation(namespace: str, key: str, lang: str) -> Optional[str]:
    """Возвращает перевод одного ключа."""
    translations = get_translations(namespace, lang)
    return translations.get(key)


def get_localized_value_from_s3(namespace: str, key_prefix: str, field_name: str, lang: str) -> Optional[str]:
    """
    Возвращает локализованное значение из S3.

    Пример: get_localized_value_from_s3("tariffs", "tariff.1", "title", "ru")
    → ищет ключ "tariff.1.title" в tariffs/ru.json
    """
    full_key = f"{key_prefix}.{field_name}"
    return get_translation(namespace, full_key, lang)


def invalidate_cache():
    """Сбрасывает кеш вручную (например, после sync задачи)."""
    global _cache_timestamp
    with _cache_lock:
        _cache.clear()
        _cache_timestamp = 0.0
