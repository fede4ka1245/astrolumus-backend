"""
Tolgee REST API v2 client.

Used by:
- Admin panel (read/write translations directly)
- Celery task (export translations to S3)
- Management commands (import existing texts)
- Context processor (get available languages)

Architecture:
- Content entities (tariffs, documents, etc.) each have their own Tolgee project.
  Project IDs are stored in settings.TOLGEE_PROJECTS = {"tariffs": 3, ...}
- Frontend/app-preview namespaces stay in the main project (settings.TOLGEE_PROJECT_ID).
- Within dedicated content projects, keys have no namespace.
"""

import json
import logging
from typing import Optional
from urllib.parse import urljoin

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT = 15  # seconds


def _base_url() -> str:
    return settings.TOLGEE_API_URL.rstrip("/")


def _headers() -> dict:
    return {
        "X-API-Key": settings.TOLGEE_API_KEY,
        "Content-Type": "application/json",
    }


def _get_project_context(namespace: str) -> tuple:
    """
    Returns (project_id, namespace_filter) for a given namespace key.

    If the namespace has a dedicated project, returns (project_id, None) —
    all keys in that project have no namespace.
    Otherwise returns (main_project_id, namespace) to filter by namespace.
    """
    projects = getattr(settings, "TOLGEE_PROJECTS", {})
    if namespace in projects:
        return projects[namespace], None
    return settings.TOLGEE_PROJECT_ID, namespace


def _project_url(project_id: int, path: str = "") -> str:
    return f"{_base_url()}/v2/projects/{project_id}{path}"


# ---------------------------------------------------------------------------
# Languages
# ---------------------------------------------------------------------------

def get_languages(project_id: Optional[int] = None) -> list:
    """
    Возвращает список языков проекта.
    [{"tag": "ru", "name": "Russian", "id": 1}, ...]
    """
    pid = project_id if project_id is not None else settings.TOLGEE_PROJECT_ID
    url = _project_url(pid, "/languages")
    resp = requests.get(url, headers=_headers(), timeout=_REQUEST_TIMEOUT,
                        params={"size": 100})
    resp.raise_for_status()
    data = resp.json()
    embedded = data.get("_embedded", {})
    return embedded.get("languages", [])


def get_language_tags(project_id: Optional[int] = None) -> list:
    """Возвращает список language tags: ['ru', 'en', ...]"""
    return [lang["tag"] for lang in get_languages(project_id)]


# ---------------------------------------------------------------------------
# Translations — read
# ---------------------------------------------------------------------------

def get_translations(namespace: str, language_tag: str) -> dict:
    """
    Возвращает все переводы для namespace + language в виде flat dict.
    {"key.name": "translated value", ...}
    """
    project_id, ns_filter = _get_project_context(namespace)
    url = _project_url(project_id, "/translations")
    translations = {}
    page = 0

    while True:
        params = {
            "languages": language_tag,
            "size": 250,
            "page": page,
        }
        if ns_filter is not None:
            params["filterNamespace"] = ns_filter

        resp = requests.get(url, headers=_headers(), params=params,
                            timeout=_REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        embedded = data.get("_embedded", {})
        keys = embedded.get("keys", [])
        if not keys:
            break

        for key_entry in keys:
            key_name = key_entry.get("keyName", "")
            lang_translations = key_entry.get("translations", {})
            lang_data = lang_translations.get(language_tag, {})
            text = lang_data.get("text")
            if text is not None:
                translations[key_name] = text

        page_meta = data.get("page", {})
        total_pages = page_meta.get("totalPages", 1)
        page += 1
        if page >= total_pages:
            break

    return translations


def get_key_translations(namespace: str, key_name: str) -> dict:
    """
    Возвращает переводы одного ключа по всем языкам.
    {"ru": "Тариф", "en": "Tariff"}
    """
    project_id, ns_filter = _get_project_context(namespace)
    url = _project_url(project_id, "/translations")
    params = {
        "filterKeyName": key_name,
        "size": 1,
    }
    if ns_filter is not None:
        params["filterNamespace"] = ns_filter

    resp = requests.get(url, headers=_headers(), params=params,
                        timeout=_REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()

    embedded = data.get("_embedded", {})
    keys = embedded.get("keys", [])
    if not keys:
        return {}

    result = {}
    lang_translations = keys[0].get("translations", {})
    for lang_tag, lang_data in lang_translations.items():
        text = lang_data.get("text")
        if text is not None:
            result[lang_tag] = text
    return result


# ---------------------------------------------------------------------------
# Translations — write
# ---------------------------------------------------------------------------

def upsert_key(namespace: str, key_name: str, translations: dict) -> dict:
    """
    Создаёт или обновляет ключ с переводами.

    translations: {"ru": "Тариф", "en": "Tariff"}
    """
    project_id, ns_filter = _get_project_context(namespace)
    url = _project_url(project_id, "/keys/import-resolvable")
    key_payload = {
        "name": key_name,
        "translations": {
            lang: {"text": text, "resolution": "OVERRIDE"}
            for lang, text in translations.items()
            if text is not None
        },
    }
    if ns_filter is not None:
        key_payload["namespace"] = ns_filter

    payload = {"keys": [key_payload]}
    resp = requests.post(url, headers=_headers(), json=payload,
                         timeout=_REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def upsert_keys_batch(namespace: str, keys_translations: dict) -> dict:
    """
    Batch upsert нескольких ключей.

    keys_translations: {
        "key.name": {"ru": "text", "en": "text"},
        ...
    }
    """
    project_id, ns_filter = _get_project_context(namespace)
    keys_payload = []
    for key_name, translations in keys_translations.items():
        key_entry = {
            "name": key_name,
            "translations": {
                lang: {"text": text, "resolution": "OVERRIDE"}
                for lang, text in translations.items()
                if text is not None
            },
        }
        if ns_filter is not None:
            key_entry["namespace"] = ns_filter
        keys_payload.append(key_entry)

    # Tolgee batch limit — split into chunks of 50
    results = []
    url = _project_url(project_id, "/keys/import-resolvable")
    for i in range(0, len(keys_payload), 50):
        chunk = keys_payload[i:i + 50]
        resp = requests.post(url, headers=_headers(),
                             json={"keys": chunk},
                             timeout=60)
        if not resp.ok:
            logger.error(
                "Tolgee batch upsert failed (chunk %d, status %d): %s",
                i // 50, resp.status_code, resp.text[:500],
            )
            # Try one by one for failed chunk
            for single_key in chunk:
                single_resp = requests.post(
                    url, headers=_headers(),
                    json={"keys": [single_key]},
                    timeout=30,
                )
                if not single_resp.ok:
                    logger.error(
                        "Tolgee single upsert failed for key '%s': %d %s",
                        single_key.get("name"), single_resp.status_code,
                        single_resp.text[:300],
                    )
            continue
        results.append(resp.json())

    return {"chunks": len(results), "total_keys": len(keys_payload)}


def delete_key(namespace: str, key_name: str) -> bool:
    """Удаляет ключ из Tolgee."""
    project_id, ns_filter = _get_project_context(namespace)
    url = _project_url(project_id, "/translations")
    params = {
        "filterKeyName": key_name,
        "size": 1,
    }
    if ns_filter is not None:
        params["filterNamespace"] = ns_filter

    resp = requests.get(url, headers=_headers(), params=params,
                        timeout=_REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()

    embedded = data.get("_embedded", {})
    keys = embedded.get("keys", [])
    if not keys:
        return False

    key_id = keys[0].get("keyId")
    if not key_id:
        return False

    delete_url = _project_url(project_id, f"/keys/{key_id}")
    resp = requests.delete(delete_url, headers=_headers(),
                           timeout=_REQUEST_TIMEOUT)
    resp.raise_for_status()
    return True


def delete_keys_by_prefix(namespace: str, prefix: str) -> int:
    """Удаляет все ключи namespace, начинающиеся с prefix."""
    project_id, ns_filter = _get_project_context(namespace)
    url = _project_url(project_id, "/translations")
    deleted = 0
    page = 0

    while True:
        params = {
            "filterKeyPrefix": prefix,
            "size": 100,
            "page": page,
        }
        if ns_filter is not None:
            params["filterNamespace"] = ns_filter

        resp = requests.get(url, headers=_headers(), params=params,
                            timeout=_REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        embedded = data.get("_embedded", {})
        keys = embedded.get("keys", [])
        if not keys:
            break

        key_ids = [k["keyId"] for k in keys if k.get("keyId")]
        if key_ids:
            delete_url = _project_url(project_id, "/keys")
            resp = requests.delete(delete_url, headers=_headers(),
                                   json={"ids": key_ids},
                                   timeout=_REQUEST_TIMEOUT)
            resp.raise_for_status()
            deleted += len(key_ids)

        page_meta = data.get("page", {})
        total_pages = page_meta.get("totalPages", 1)
        page += 1
        if page >= total_pages:
            break

    return deleted


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_namespace(namespace: str, format: str = "JSON") -> dict:
    """
    Экспортирует все переводы namespace.
    Возвращает: {"ru": {"key": "value", ...}, "en": {...}}
    """
    project_id, ns_filter = _get_project_context(namespace)
    url = _project_url(project_id, "/export")
    params = {
        "format": format,
        "structureDelimiter": "",  # flat keys
    }
    if ns_filter is not None:
        params["filterNamespace"] = ns_filter

    resp = requests.get(url, headers=_headers(), params=params,
                        timeout=30, stream=True)
    if resp.status_code == 400:
        # Tolgee returns 400 when namespace/project is empty — treat as empty
        return {}
    resp.raise_for_status()

    import io
    import zipfile

    result = {}
    zip_buffer = io.BytesIO(resp.content)
    try:
        with zipfile.ZipFile(zip_buffer) as zf:
            for file_info in zf.infolist():
                if file_info.filename.endswith(".json"):
                    name = file_info.filename
                    lang_tag = name.rsplit("/", 1)[-1].replace(".json", "")
                    with zf.open(file_info) as f:
                        content = json.loads(f.read().decode("utf-8"))
                        result[lang_tag] = content
    except Exception:
        return {}

    return result


def export_namespace_nested(namespace: str) -> dict:
    """
    Экспортирует все переводы namespace с nested структурой (для i18next).
    Возвращает: {"ru": {"common": {"back": "Назад"}}, "en": {...}}
    """
    project_id, ns_filter = _get_project_context(namespace)
    url = _project_url(project_id, "/export")
    params = {
        "format": "JSON",
        "structureDelimiter": ".",  # nested by dot
    }
    if ns_filter is not None:
        params["filterNamespace"] = ns_filter

    resp = requests.get(url, headers=_headers(), params=params,
                        timeout=30, stream=True)
    if resp.status_code == 400:
        return {}
    resp.raise_for_status()

    import io
    import zipfile

    result = {}
    zip_buffer = io.BytesIO(resp.content)
    try:
        with zipfile.ZipFile(zip_buffer) as zf:
            for file_info in zf.infolist():
                if file_info.filename.endswith(".json"):
                    name = file_info.filename
                    lang_tag = name.rsplit("/", 1)[-1].replace(".json", "")
                    with zf.open(file_info) as f:
                        content = json.loads(f.read().decode("utf-8"))
                        result[lang_tag] = content
    except Exception:
        return {}

    return result
