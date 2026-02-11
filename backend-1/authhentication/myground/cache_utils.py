# cache_utils.py
from django.conf import settings
from django.core.cache import cache

class ResourceCache:
    """Cache management for AWS resources using Django's cache framework"""
    
    @staticmethod
    def get_resources_cache_key(account_id):
        return f"aws_resources_{account_id}"
    
    @staticmethod
    def get_resource_summary_cache_key(account_id):
        return f"aws_resource_summary_{account_id}"
    
    @staticmethod
    def get_cost_analytics_cache_key(account_id):
        return f"aws_cost_analytics_{account_id}"
    
    @staticmethod
    def cache_resources(account_id, resources_data):
        """Cache AWS resources data"""
        try:
            cache_key = ResourceCache.get_resources_cache_key(account_id)
            cache.set(cache_key, resources_data, settings.RESOURCE_CACHE_TTL)
            return True
        except Exception as e:
            print(f"⚠️ Cache set failed for resources: {e}")
            return False
    
    @staticmethod
    def get_cached_resources(account_id):
        """Get cached AWS resources"""
        try:
            cache_key = ResourceCache.get_resources_cache_key(account_id)
            return cache.get(cache_key)
        except Exception as e:
            print(f"⚠️ Cache get failed for resources: {e}")
            return None
    
    @staticmethod
    def cache_resource_summary(account_id, summary_data):
        """Cache resource summary data"""
        try:
            cache_key = ResourceCache.get_resource_summary_cache_key(account_id)
            cache.set(cache_key, summary_data, settings.RESOURCE_CACHE_TTL)
            return True
        except Exception as e:
            print(f"⚠️ Cache set failed for summary: {e}")
            return False
    
    @staticmethod
    def get_cached_resource_summary(account_id):
        """Get cached resource summary"""
        try:
            cache_key = ResourceCache.get_resource_summary_cache_key(account_id)
            return cache.get(cache_key)
        except Exception as e:
            print(f"⚠️ Cache get failed for summary: {e}")
            return None
    
    @staticmethod
    def cache_cost_analytics(account_id, analytics_data):
        """Cache cost analytics data"""
        try:
            cache_key = ResourceCache.get_cost_analytics_cache_key(account_id)
            cache.set(cache_key, analytics_data, settings.COST_CACHE_TTL)
            return True
        except Exception as e:
            print(f"⚠️ Cache set failed for analytics: {e}")
            return False
    
    @staticmethod
    def get_cached_cost_analytics(account_id):
        """Get cached cost analytics"""
        try:
            cache_key = ResourceCache.get_cost_analytics_cache_key(account_id)
            return cache.get(cache_key)
        except Exception as e:
            print(f"⚠️ Cache get failed for analytics: {e}")
            return None
    
    @staticmethod
    def invalidate_account_cache(account_id):
        """Invalidate all cache for an account"""
        try:
            keys = [
                ResourceCache.get_resources_cache_key(account_id),
                ResourceCache.get_resource_summary_cache_key(account_id),
                ResourceCache.get_cost_analytics_cache_key(account_id),
            ]
            cache.delete_many(keys)
            return True
        except Exception as e:
            print(f"⚠️ Cache delete failed: {e}")
            return False