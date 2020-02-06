from django.db import models

from typing import Optional, Any

from django.db import models


class ScopedPermission(models.Model):
    scope = models.TextField(unique=True, blank=False)

    def get_scope_parts(self):
        return self.scope.split(":")

    def __str__(self):
        return self.scope


class HasScopedPermissionsMixin(models.Model):
    class Meta:
        abstract = True

    scoped_permissions = models.ManyToManyField(ScopedPermission, blank=True,)

    def get_scopes(self):
        specific_scopes = list(self.scoped_permissions.values_list("scope", flat=True))

        return specific_scopes


class ScopedModelMixin(models.Model):
    """Mixin for a model with scoped permission."""

    class Meta:
        abstract = True

    def get_base_scopes(self):
        return []

    def has_permission(
        self, user: HasScopedPermissionsMixin, action: Optional[str] = None
    ):
        user_scopes = user.get_scopes()
        base_scopes = self.get_base_scopes()
        base_scopes = expand_scopes_with_action(base_scopes, action)

        return any_scope_matches(base_scopes, user_scopes)

