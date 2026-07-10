"""
RoadWatch — reports/signals.py
Auto-creates a Profile record when a new User is registered.
"""

from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import Profile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a Profile record the first time a User is saved."""
    if created:
        Profile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Ensure the Profile is saved whenever the User is saved."""
    if hasattr(instance, 'profile'):
        instance.profile.save()
