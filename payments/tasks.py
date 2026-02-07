"""
Celery tasks for payment processing and subscription management
"""
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db.models import F
from django.utils import timezone
from celery import shared_task
import logging

from tariffs.models import Tariff, ActivationTariff

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task
def activate_user_tariff(user_id: int, tariff_code: str, order_id: str = None):
    """
    Activate a tariff for a user after successful payment.
    This task is called by webhook handlers (StripeCallbackView, BepaidCallBackView)
    
    Args:
        user_id: ID of the user
        tariff_code: Code of the tariff to activate (e.g., "monthly_pro")
    """
    try:
        user = User.objects.get(id=user_id)
        tariff = Tariff.objects.get(code=tariff_code)
        existing = ActivationTariff.objects.filter(
            user=user,
            tariff=tariff
        ).order_by('-created_at').first()
        
        if existing:
            expiration_date = existing.created_at + timedelta(days=tariff.validity_days) if tariff.validity_days > 0 else None
            
            if expiration_date and timezone.now() < expiration_date:
                logger.info(f"ℹ️ User {user.email} already has active tariff '{tariff_code}' (expires: {expiration_date})")
        
        # Create activation record
        activation = ActivationTariff.objects.create(user=user, tariff=tariff)
        
        logger.info(f"✅ Tariff '{tariff_code}' activated for user {user.email} (ID: {user_id}, Order: {order_id})")
        logger.info(f"📅 Activation ID: {activation.id}, Created: {activation.created_at}")
        
        if tariff.validity_days > 0:
            expiration = activation.created_at + timedelta(days=tariff.validity_days)
            logger.info(f"⏰ Tariff valid until: {expiration}")
        else:
            logger.info(f"♾️ Tariff is lifetime (no expiration)")
        
        return {
            'status': 'success',
            'activation_id': activation.id,
            'tariff': tariff.title,
            'tariff_code': tariff_code,
            'user_email': user.email,
            'user_id': user_id,
            'order_id': order_id,
            'created_at': activation.created_at.isoformat(),
            'validity_days': tariff.validity_days
        }
    
    except User.DoesNotExist:
        logger.error(f"❌ User not found: ID {user_id}")
        return {'status': 'error', 'message': f'User {user_id} not found'}
    
    except Tariff.DoesNotExist:
        logger.error(f"❌ Tariff not found: code {tariff_code}")
        return {'status': 'error', 'message': f'Tariff {tariff_code} not found'}
    
    except Exception as e:
        logger.error(f"❌ Error activating tariff: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def check_subscription_expiration():
    """
    Periodic task: Check for expired subscriptions (runs daily).
    Identifies tariffs that have passed their validity period.
    
    Celery Beat Schedule (in settings.py):
    'check-subscription-expiration': {
        'task': 'payments.tasks.check_subscription_expiration',
        'schedule': crontab(hour=0, minute=0),  # Daily at midnight UTC
    }
    """
    try:
        # Find all active tariffs that have expired
        # Only check tariffs with validity_days > 0 (not lifetime subscriptions)
        expired_activations = ActivationTariff.objects.filter(
            tariff__validity_days__gt=0,
            created_at__lt=timezone.now() - timedelta(days=F('tariff__validity_days'))
        )
        
        count = expired_activations.count()
        logger.info(f"Found {count} expired subscriptions")
        
        return {
            'status': 'success',
            'expired_count': count,
            'timestamp': timezone.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"❌ Error checking subscription expiration: {str(e)}")
        return {'status': 'error', 'message': str(e)}

