import os
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from .models import Certificate


@receiver(pre_delete, sender=Certificate)
def delete_certificate_file(sender, instance, **kwargs):
    """
    Delete the certificate file from filesystem when Certificate object is deleted.
    """
    if instance.certificate_file:
        # Delete the file if it exists
        if os.path.isfile(instance.certificate_file.path):
            os.remove(instance.certificate_file.path)

