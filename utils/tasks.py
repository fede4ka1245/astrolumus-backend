"""
Celery tasks for Tolgee → S3 translation sync.
"""

import io
import json
import logging

from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)

# All namespaces — each has its own dedicated Tolgee project (settings.TOLGEE_PROJECTS)
# frontend/app-preview use nested JSON (for i18next); content entities use flat JSON
PROJECTS = {
    "frontend": "nested",
    "app-preview": "nested",
    "tariffs": "flat",
    "documents": "flat",
    "app_info": "flat",
    "astroprocessor_types": "flat",
    "astroprocessor_data": "flat",
    "sign_planet": "flat",
    "planet_house": "flat",
    "master_house": "flat",
    "constellations": "flat",
    "stellar_types": "flat",
    "stars": "flat",
    "sky_info": "flat",
}


def _get_minio_client():
    from minio import Minio

    return Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_USE_HTTPS,
    )


def _upload_json_to_s3(client, bucket: str, path: str, data: dict):
    content = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    stream = io.BytesIO(content)
    client.put_object(
        bucket,
        path,
        stream,
        length=len(content),
        content_type="application/json",
    )


@shared_task
def sync_tolgee_to_s3():
    """
    Экспортирует переводы из всех Tolgee проектов и загружает JSON файлы в S3.

    Каждый namespace имеет свой отдельный Tolgee проект (TOLGEE_PROJECTS).
    Ключи в проектах не имеют namespace.

    Структура в S3:
      alpha/translations/{namespace}/{lang}.json
    """
    from utils.tolgee_client import export_namespace, export_namespace_nested

    prefix = settings.TOLGEE_TRANSLATIONS_S3_PREFIX
    bucket = "alpha"

    try:
        client = _get_minio_client()
    except Exception as e:
        logger.error("Failed to connect to MinIO: %s", e)
        return {"status": "error", "message": str(e)}

    results = {}

    for namespace, mode in PROJECTS.items():
        try:
            if mode == "nested":
                data = export_namespace_nested(namespace)
            else:
                data = export_namespace(namespace)

            if not data:
                logger.info("Project '%s' is empty, skipping", namespace)
                results[namespace] = "empty"
                continue

            for lang_tag, translations in data.items():
                s3_path = f"{prefix}/{namespace}/{lang_tag}.json"
                _upload_json_to_s3(client, bucket, s3_path, translations)

            results[namespace] = {"languages": list(data.keys()), "status": "ok"}
            logger.info("Exported project '%s': %d languages", namespace, len(data))
        except Exception as e:
            logger.error("Failed to export project '%s': %s", namespace, e)
            results[namespace] = {"status": "error", "message": str(e)}

    return results
