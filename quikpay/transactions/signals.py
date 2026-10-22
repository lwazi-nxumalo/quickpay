from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Wallet

User = get_user_model()


@receiver(post_save, sender=User)
def provision_wallet_on_user_activation(sender, instance, created, **kwargs):
  """Signals the transactions app to safely provision a wallet

  when a user's status is set to active (whether newly created or re-activated).
  """
  # Check if the user is active based on your user status field
  if getattr(instance, "status", None) == "active":
    Wallet.objects.get_or_create(user=instance)