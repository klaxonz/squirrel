"""
缓存管理器实现
"""
import logging
import json
from typing import Any, Optional
from datetime import datetime, timedelta

from core.cache import RedisClient
from .interfaces import ICacheManager

logger = logging.getLogger()


class RedisCacheManager(ICacheManager):
    """基于Redis的缓存管理器"""
    
    def __init__(self, prefix: str = "extraction", default_ttl: int = 3600):
        self.client = RedisClient.get_instance().get_client()
        self.prefix = prefix
        self.default_ttl = default_ttl
    
    def _make_key(self, key: str) -> str:
        """生成完整的缓存键"""
        return f"{self.prefix}:{key}"
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        try:
            full_key = self._make_key(key)
            value = self.client.get(full_key)
            if value is None:
                return None
            
            # 尝试JSON解析，如果失败则返回原始字符串
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value.decode('utf-8') if isinstance(value, bytes) else value
                
        except Exception as e:
            logger.error(f"获取缓存失败: {key}, error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存"""
        try:
            full_key = self._make_key(key)
            ttl = ttl or self.default_ttl
            
            # 序列化值
            if isinstance(value, (dict, list, tuple)):
                serialized_value = json.dumps(value, ensure_ascii=False)
            elif isinstance(value, (int, float, bool)):
                serialized_value = json.dumps(value)
            else:
                serialized_value = str(value)
            
            self.client.setex(full_key, ttl, serialized_value)
            logger.debug(f"设置缓存: {key}, ttl: {ttl}")
            
        except Exception as e:
            logger.error(f"设置缓存失败: {key}, error: {e}")
    
    def delete(self, key: str) -> None:
        """删除缓存"""
        try:
            full_key = self._make_key(key)
            self.client.delete(full_key)
            logger.debug(f"删除缓存: {key}")
        except Exception as e:
            logger.error(f"删除缓存失败: {key}, error: {e}")
    
    def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        try:
            full_key = self._make_key(key)
            return bool(self.client.exists(full_key))
        except Exception as e:
            logger.error(f"检查缓存存在性失败: {key}, error: {e}")
            return False
    
    def expire(self, key: str, ttl: int) -> None:
        """设置缓存过期时间"""
        try:
            full_key = self._make_key(key)
            self.client.expire(full_key, ttl)
        except Exception as e:
            logger.error(f"设置缓存过期时间失败: {key}, error: {e}")
    
    def get_ttl(self, key: str) -> int:
        """获取缓存剩余时间"""
        try:
            full_key = self._make_key(key)
            return self.client.ttl(full_key)
        except Exception as e:
            logger.error(f"获取缓存TTL失败: {key}, error: {e}")
            return -1
    
    def clear_pattern(self, pattern: str) -> int:
        """根据模式清除缓存"""
        try:
            full_pattern = self._make_key(pattern)
            keys = self.client.keys(full_pattern)
            if keys:
                deleted = self.client.delete(*keys)
                logger.info(f"清除缓存: {pattern}, 删除数量: {deleted}")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"清除缓存失败: {pattern}, error: {e}")
            return 0


class MemoryCacheManager(ICacheManager):
    """基于内存的缓存管理器（用于测试）"""
    
    def __init__(self, default_ttl: int = 3600):
        self._cache = {}
        self._expire_times = {}
        self.default_ttl = default_ttl
    
    def _is_expired(self, key: str) -> bool:
        """检查是否过期"""
        if key not in self._expire_times:
            return False
        return datetime.now() > self._expire_times[key]
    
    def _cleanup_expired(self, key: str) -> None:
        """清理过期缓存"""
        if self._is_expired(key):
            self._cache.pop(key, None)
            self._expire_times.pop(key, None)
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        self._cleanup_expired(key)
        return self._cache.get(key)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存"""
        self._cache[key] = value
        ttl = ttl or self.default_ttl
        self._expire_times[key] = datetime.now() + timedelta(seconds=ttl)
    
    def delete(self, key: str) -> None:
        """删除缓存"""
        self._cache.pop(key, None)
        self._expire_times.pop(key, None)
    
    def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        self._cleanup_expired(key)
        return key in self._cache
    
    def clear(self) -> None:
        """清空所有缓存"""
        self._cache.clear()
        self._expire_times.clear()


# 缓存键常量
class CacheKeys:
    """缓存键常量"""
    
    # 任务相关
    TASK_PROCESSING = "task:processing:{url}"
    TASK_RESULT = "task:result:{task_id}"
    TASK_PROGRESS = "task:progress:{task_id}"
    
    # 提取相关
    EXTRACT_RESULT = "extract:result:{url}"
    EXTRACT_METADATA = "extract:metadata:{url}"
    
    # 网站相关
    SITE_CONFIG = "site:config:{site_name}"
    SITE_COOKIES = "site:cookies:{site_name}"
    
    # 限流相关
    RATE_LIMIT = "rate_limit:{site_name}:{identifier}"
    
    @classmethod
    def format_key(cls, template: str, **kwargs) -> str:
        """格式化缓存键"""
        return template.format(**kwargs)
