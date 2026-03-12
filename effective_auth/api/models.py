from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    """
    Stores an explicit role for each user.
    This is used for RBAC demos on top of the built-in User flags.
    """

    class Role(models.TextChoices):
        USER = "user", "User"
        MANAGER = "manager", "Manager"
        ADMIN = "admin", "Admin"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.USER,
    )

    def __str__(self) -> str:
        return f"{self.user.email or self.user.username} ({self.role})"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_profile_role_for_superuser(sender, instance, created, **kwargs):
    """
    Ensure every user has a profile and that superusers default to admin role.
    """
    # Get or create profile for this user
    profile, _ = UserProfile.objects.get_or_create(user=instance)

    # If the user is a superuser, enforce admin role
    if getattr(instance, "is_superuser", False) and profile.role != UserProfile.Role.ADMIN:
        profile.role = UserProfile.Role.ADMIN
        profile.save(update_fields=["role"])
