from typing import Optional

from django.db import models
from django.db.models import Value, F, Case, When
from django.db.models.functions import Concat
from django.utils.functional import cached_property

from django_scoped_permissions.core import any_scope_matches, scopes_grant_permissions


class ScopedPermission(models.Model):
    class Meta:
        unique_together = (("scope", "exclude", "exact"),)

    scope = models.TextField(blank=False)
    exclude = models.BooleanField(
        default=False,
        help_text="Whether this should be an exclusive permission, meaning that if scope is 'user:update' and exclude is True then users with this usertype will not be able to update users, even their own.",
    )
    exact = models.BooleanField(
        default=False,
        help_text="If checked, the permission needs an exact match to count. In other words, it does not work recursively as standard scoped permissions.",
    )

    def get_scope_parts(self):
        return self.scope.split(":")

    def __str__(self):
        prefix = "-" if self.exclude else ""
        prefix += "=" if self.exact else ""
        return prefix + self.scope


class ScopedPermissionGroup(models.Model):
    name = models.TextField()
    scoped_permissions = models.ManyToManyField(
        ScopedPermission, blank=True, related_name="in_groups"
    )

    def __str__(self):
        return self.name


class HasScopedPermissionsMixin(models.Model):
    class Meta:
        abstract = True

    scoped_permissions = models.ManyToManyField(ScopedPermission, blank=True)
    scoped_permission_groups = models.ManyToManyField(ScopedPermissionGroup, blank=True)

    @cached_property
    def resolved_group_scopes(self):
        scopes = ScopedPermission.objects.filter(
            in_groups__in=self.scoped_permission_groups.all()
        )
        scopes = scopes.annotate(
            parsed_scope=Concat(
                Case(When(exclude=True, then=Value("-")), default=Value("")),
                Case(When(exact=True, then=Value("=")), default=Value("")),
                F("scope"),
            )
        )

        return list(scopes.values_list("parsed_scope", flat=True))

    @cached_property
    def resolved_scopes(self):
        scopes = self.scoped_permissions.all() | ScopedPermission.objects.filter(
            in_groups__in=self.scoped_permission_groups.all()
        )
        scopes = scopes.annotate(
            parsed_scope=Concat(
                Case(When(exclude=True, then=Value("-")), default=Value("")),
                Case(When(exact=True, then=Value("=")), default=Value("")),
                F("scope"),
            )
        )

        resolved_scopes = list(scopes.values_list("parsed_scope", flat=True))

        return resolved_scopes

    def get_scopes(self):
        """
        DEPRECATED: Use `get_granting_scopes` instead
        """
        return self.resolved_scopes

    def get_granting_scopes(self):
        return self.resolved_scopes

    def has_scoped_permissions(self, *required_scopes):
        return self.has_any_scoped_permissions(*required_scopes)

    def has_any_scoped_permissions(self, *required_scopes):
        scopes = self.get_scopes()

        return scopes_grant_permissions(required_scopes, scopes)

    def has_all_scoped_permissions(self, *required_scopes):
        scopes = self.get_scopes()

        for scope in required_scopes:
            if not any_scope_matches([scope], scopes):
                return False

        return True

    def has_create_permission(self, model_name: str, action: str = "create"):
        scopes = self.get_scopes()
        return f"-{model_name}:{action}" not in scopes


class ScopedModelMixin:
    def get_base_scopes(self):
        """
        DEPRECATED: Use `get_required_scopes`
        """
        return self.get_required_scopes()

    def get_required_scopes(self):
        return []

    def has_permission(
        self, user: HasScopedPermissionsMixin, action: Optional[str] = None
    ):
        if getattr(user, "is_superuser", False):
            return True

        user_scopes = user.get_granting_scopes()
        base_scopes = self.get_required_scopes()

        return scopes_grant_permissions(base_scopes, user_scopes, action)


class ScopedModel(models.Model, ScopedModelMixin):
    class Meta:
        abstract = True
