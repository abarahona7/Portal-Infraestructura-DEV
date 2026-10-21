from django.contrib.auth.models import AnonymousUser, User
from django.test import SimpleTestCase
from django.utils.functional import SimpleLazyObject

from core.audit import (
    get_current_audit_username,
    reset_current_audit_user,
    set_current_audit_user,
)


class AuditContextTests(SimpleTestCase):
    def test_lazy_authenticated_user_is_reduced_to_username(self):
        lazy_user = SimpleLazyObject(lambda: User(username='admin-auditoria'))

        token = set_current_audit_user(lazy_user)
        try:
            self.assertEqual(get_current_audit_username(), 'admin-auditoria')
        finally:
            reset_current_audit_user(token)

    def test_anonymous_user_does_not_become_audit_actor(self):
        token = set_current_audit_user(AnonymousUser())
        try:
            self.assertIsNone(get_current_audit_username())
        finally:
            reset_current_audit_user(token)
