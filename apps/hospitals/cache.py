from django.core.cache import cache

HOSPITAL_LIST_CACHE_KEY = "hospitals:list:v1"
HOSPITAL_LIST_CACHE_TTL = 60 * 15


def invalidate_hospital_list_cache():
    cache.delete(HOSPITAL_LIST_CACHE_KEY)
