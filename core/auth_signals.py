"""Revoca credenciales cuando cambia la seguridad de una cuenta."""

from django.contrib.auth import get_user_model
from django.db.models.signals import m2m_changed, post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from .models import PortalSession
from .session_events import notify_session_revoked


User = get_user_model()


def revoke_all_user_sessions(user_id):
    active_sessions = list(PortalSession.objects.filter(
        user_id=user_id,
        revoked_at__isnull=True,
    ).values_list('pk', flat=True))
    PortalSession.objects.filter(pk__in=active_sessions).update(revoked_at=timezone.now())
    for session_id in active_sessions:
        notify_session_revoked(session_id)
    for token in OutstandingToken.objects.filter(user_id=user_id).iterator():
        BlacklistedToken.objects.get_or_create(token=token)


@receiver(pre_save, sender=User)
def remember_security_fields(sender, instance, **kwargs):
    if not instance.pk:
        instance._portal_security_changed = False
        return
    try:
        previous = sender.objects.only('password', 'is_active', 'is_superuser').get(pk=instance.pk)
    except sender.DoesNotExist:
        instance._portal_security_changed = False
        return
    instance._portal_security_changed = any((
        previous.password != instance.password,
        previous.is_active != instance.is_active,
        previous.is_superuser != instance.is_superuser,
    ))


@receiver(post_save, sender=User)
def revoke_after_account_security_change(sender, instance, created, **kwargs):
    if not created and getattr(instance, '_portal_security_changed', False):
        revoke_all_user_sessions(instance.pk)


@receiver(m2m_changed, sender=User.groups.through)
def revoke_after_group_change(sender, instance, action, reverse, pk_set, **kwargs):
    if action == 'pre_clear' and reverse:
        instance._portal_cleared_user_ids = list(instance.user_set.values_list('pk', flat=True))
        return
    if action not in {'post_add', 'post_remove', 'post_clear'}:
        return
    if reverse:
        user_ids = pk_set or getattr(instance, '_portal_cleared_user_ids', ())
    else:
        user_ids = (instance.pk,)
        if hasattr(instance, '_portal_role_cache'):
            delattr(instance, '_portal_role_cache')
    for user_id in user_ids:
        revoke_all_user_sessions(user_id)
