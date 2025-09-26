"""
缓存管理器实现
"""
import logging
import json
from typing import Any, Optional
from datetime import datetime, timedelta

from core.cache import RedisClient
from core.extraction.task_manager import ICacheManager

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
    

