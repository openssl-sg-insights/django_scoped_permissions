from django.db import models
from django.db.models import Value, F, Case, When
from django.db.models.functions import Concat

from typing import Optional, Any

from permissions.util import any_scope_matches, expand_scopes_with_action


class ScopedPermission(models.Model):
    class Meta:
        unique_together = (("scope", "exclude"),)

    scope = models.TextField(blank=False)
    exclude = models.BooleanField(
        default=False,
        help_text="Whether this should be an exclusive permission, meaning that if scope is 'user:update' and exclude is True then users with this usertype will not be able to update users, even their own.",
    )
    exact = models.BooleanField(
        default=False,
        help_text="If checked, the permission needs an exact match to count. In other words, it does not work recursively as standard scoped permissions."
    )

    def get_scope_parts(self):
        return self.scope.split(":")

    def __str__(self):
        prefix = ("-" if self.exclude else "")
        prefix += ("=" if self.exact else "")
        return prefix + self.scope


class HasScopedPermissionsMixin(models.Model):
    class Meta:
        abstract = True

    scoped_permissions = models.ManyToManyField(ScopedPermission, blank=True,)

    def get_scopes(self):
        scopes = self.scoped_permissions
        scopes = scopes.annotate(
            parsed_scope=Concat(
                Case(When(exclude=True, then=Value("-")), default=Value("")),
                Case(When(exact=True, then=Value("=")), default=Value("")),
                F("scope")
            )
        )

        specific_scopes = list(scopes.values_list("parsed_scope", flat=True))

        return specific_scopes


    def has_scoped_permissions(self, *required_scopes):
        return self.has_any_scoped_permissions(*required_scopes)

    def has_any_scoped_permissions(self, *required_scopes):
        scopes = self.get_scopes()

        return any_scope_matches(required_scopes, scopes)

    def has_all_scoped_permissions(self, *required_scopes):
        scopes = self.get_scopes()

        for scope in required_scopes:
            if not any_scope_matches([scope], scopes):
                print(scope, scopes)
                return False

        return True

    def has_create_permission(self, model_name: str, action: str = "create"):
        scopes = self.get_scopes()
        return f"-{model_name}:{action}" not in scopes


class ScopedModelMixin(models.Model):
    """Mixin for a model with scoped permission."""

    class Meta:
        abstract = True

    def get_base_scopes(self):
        return []

    def has_permission(
        self, user: HasScopedPermissionsMixin, action: Optional[str] = None
    ):
        if getattr(user, "is_superuser", False):
            return True

        user_scopes = user.get_scopes()
        base_scopes = self.get_base_scopes()
        base_scopes = expand_scopes_with_action(base_scopes, action)

        return any_scope_matches(base_scopes, user_scopes)

