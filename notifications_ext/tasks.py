from django.contrib.auth import get_user_model
from django.conf import settings
from django.db import transaction

from celery import shared_task
from firebase_admin.messaging import Message, Notification as PushNotification
from fcm_django.models import FCMDevice, _validate_exception_for_deactivation
from notifications.models import Notification as InnerNotification
import sentry_sdk
import logging

from django.utils.html import strip_tags

from misc.constants import USER_CONTENT_TYPE_ID
from utils.multilinguality import get_language_value
from .models import NotificationTask

User = get_user_model()


@shared_task
def notification_task():
    for _ in range(NotificationTask.objects.filter(sent=False).count()):
        with transaction.atomic():
            _send_notification(
                NotificationTask.objects.select_for_update(skip_locked=True).filter(sent=False).order_by("id")[:1].first()
            )


def _send_notification(task):
    if task is None:
        return

    _send_inner_notification(task)
    _send_push_notification(task)

    task.sent = True
    task.save()


def _send_inner_notification(task):
    notification_pages_by_language_code = {page.language_code.code: page.id for page in task.pages_group.pages.all()}
    InnerNotification.objects.bulk_create(
        (
            InnerNotification(
                level=task.level,
                recipient_id=recipient.id,
                unread=task.unread,
                actor_content_type_id=USER_CONTENT_TYPE_ID,
                actor_object_id=settings.SCHOOL_USER_ID,
                verb=strip_tags(get_language_value(task.verb, recipient.app_language.code) or "").strip(),
                description=strip_tags(get_language_value(task.description, recipient.app_language.code) or "").strip(),
                target_content_type=task.target_content_type,
                target_object_id=task.target_object_id,
                action_object_content_type=task.action_object_content_type,
                action_object_object_id=task.action_object_object_id,
                timestamp=task.timestamp,
                public=task.public,
                deleted=task.deleted,
                emailed=task.emailed,
                data=(task.data if task.data else {}) | {
                    # TODO uncomment
                    # 'notification_page_id': get_language_value(
                    #     notification_pages_by_language_code,
                    #     recipient.app_language.code
                    # )
                } | _remove_me_a_year_later(notification_pages_by_language_code, recipient)
            ) for recipient in User.objects.select_related('app_language').all()
        ),
        batch_size=1000
    )

# TODO remove this after all users updated to new version, uncomment that ^
# this is here for backward compatibility purpose only
def _remove_me_a_year_later(notification_pages_by_language_code, recipient):
    notification_page = get_language_value(
                        notification_pages_by_language_code,
                        recipient.app_language.code
                    )
    return {'notification_page_id': notification_page, 'notificationPageId': notification_page}

def _send_push_notification(task):
    message_data = {
        'verb': task.verb,
        'body': task.description,
        # 'level': task.level,
        # 'public': task.public,
        # 'deleted': task.deleted,
        # 'emailed': task.emailed,
        # 'data': task.data
    }
    fcm_devices = FCMDevice.objects.select_related('user').prefetch_related('user__app_language').all()
    for i in range(3):
        fcm_devices = _send_push_notification_to_devices(message_data, fcm_devices)
        if not fcm_devices:
            break


def _send_push_notification_to_devices(message_data, fcm_devices):
    error_devices_q = []
    for fcm_device in fcm_devices:
        try:
            recipient_language_code = fcm_device.user.app_language.code
            fcm_device.send_message(
                Message(
                    notification=PushNotification(
                        title=strip_tags(get_language_value(message_data.get('verb', {}), recipient_language_code) or "").strip(),
                        body=strip_tags(get_language_value(message_data.get('body', {}), recipient_language_code) or "").strip(),
                    )
                    # data=message_data # Message.data must not contain non-string values.
                )
            )
        except Exception as e:
            if settings.FCM_DJANGO_SETTINGS["DELETE_INACTIVE_DEVICES"] and _validate_exception_for_deactivation(e):
                fcm_device.delete()
                continue
            logging.error(e)
            sentry_sdk.capture_exception(e)
            error_devices_q.append(fcm_device)
    return error_devices_q
