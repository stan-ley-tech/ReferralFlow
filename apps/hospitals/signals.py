from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.hospitals.cache import invalidate_hospital_list_cache
from apps.hospitals.models import Department, Hospital


@receiver([post_save, post_delete], sender=Hospital)
def clear_hospital_cache_on_hospital_change(sender, **kwargs):
    invalidate_hospital_list_cache()


@receiver([post_save, post_delete], sender=Department)
def clear_hospital_cache_on_department_change(sender, **kwargs):
    invalidate_hospital_list_cache()
