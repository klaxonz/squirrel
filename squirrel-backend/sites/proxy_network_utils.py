import asyncio
import logging
from typing import Dict, Tuple

import httpx

logger = logging.getLogger(__name__)


class NetworkOptimizer:
    """网络优化工具类"""
    
    @staticmethod
    def get_optimal_chunk_size(content_length: int, content_type: str = "") -> int:
        """根据内容大小和类型获取最优块大小"""
        content_type = content_type.lower()
        
        # 视频/音频文件使用更大的块
        if 'video' in content_type or 'audio' in content_type:
            if content_length > 500 * 1024 * 1024:  # > 500MB
                return 8 * 1024 * 1024  # 8MB chunks
            elif content_length > 100 * 1024 * 1024:  # > 100MB
                return 4 * 1024 * 1024  # 4MB chunks
            else:
                return 2 * 1024 * 1024  # 2MB chunks
        
        # 普通文件
        if content_length > 100 * 1024 * 1024:  # > 100MB
            return 2 * 1024 * 1024  # 2MB chunks
        elif content_length > 10 * 1024 * 1024:  # > 10MB
            return 1024 * 1024  # 1MB chunks
        else:
            return 512 * 1024  # 512KB chunks
    
    @staticmethod
    def get_optimal_timeout(domain: str, content_length: int = 0) -> Tuple[float, float, float]:
        """获取最优超时配置 (connect_timeout, read_timeout, total_timeout)"""
        # 基础超时配置
        base_connect = 30.0
        base_read = 120.0
        
        # 根据域名调整
        domain_multipliers = {
            'pornhub.com': 1.5,  # 通常较慢
            'javdb.com': 1.3,   # 中等速度
            'bilibili.com': 1.0  # 相对较快
        }
        
        multiplier = domain_multipliers.get(domain, 1.2)
        
        # 根据文件大小调整读取超时
        if content_length > 500 * 1024 * 1024:  # > 500MB
            read_multiplier = 2.0
        elif content_length > 100 * 1024 * 1024:  # > 100MB
            read_multiplier = 1.5
        else:
            read_multiplier = 1.0
        
        connect_timeout = base_connect * multiplier
        read_timeout = base_read * multiplier * read_multiplier
        total_timeout = read_timeout + connect_timeout
        
        return connect_timeout, read_timeout, total_timeout
    
    @staticmethod
    def get_retry_config(domain: str) -> Tuple[int, float]:
        """获取重试配置 (max_retries, base_delay)"""
        retry_configs = {
            'pornhub.com': (7, 2.0),   # 更多重试，较长延迟
            'javdb.com': (6, 1.5),    # 中等重试
            'bilibili.com': (5, 1.0)  # 较少重试，较短延迟
        }
        
        return retry_configs.get(domain, (5, 1.5))
    
    @staticmethod
    def should_use_range_requests(content_length: int, content_type: str = "") -> bool:
        """判断是否应该使用范围请求"""
        # 大文件或媒体文件建议使用范围请求
        if content_length > 50 * 1024 * 1024:  # > 50MB
            return True
        
        content_type = content_type.lower()
        if 'video' in content_type or 'audio' in content_type:
            return True
            
        return False


class AdaptiveRetryStrategy:
    """自适应重试策略"""
    
    def __init__(self, domain: str):
        self.domain = domain
        self.max_retries, self.base_delay = NetworkOptimizer.get_retry_config(domain)
        self.attempt_count = 0
        self.success_count = 0
        self.failure_count = 0
    
    def get_delay(self, attempt: int) -> float:
        """获取重试延迟"""
        # 指数退避 + 抖动
        base_delay = min(self.base_delay * (2 ** attempt), 30.0)  # 最大30秒
        jitter = (asyncio.get_event_loop().time() % 1) * 0.5  # 0-0.5秒抖动
        return base_delay + jitter
    
    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """判断是否应该重试"""
        if attempt >= self.max_retries:
            return False
        
        # 定义可重试的异常
        retryable_exceptions = (
            httpx.NetworkError,
            httpx.TimeoutException,
            httpx.StreamClosed,
            httpx.RequestError,
            httpx.ConnectError,
            httpx.ReadError,
            httpx.WriteError,
            httpx.PoolTimeout,
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
            httpx.WriteTimeout,
            asyncio.TimeoutError
        )
        
        return isinstance(exception, retryable_exceptions)
    
    def record_success(self):
        """记录成功"""
        self.success_count += 1
        self.attempt_count += 1
    
    def record_failure(self):
        """记录失败"""
        self.failure_count += 1
        self.attempt_count += 1
    
    def get_success_rate(self) -> float:
        """获取成功率"""
        if self.attempt_count == 0:
            return 1.0
        return self.success_count / self.attempt_count


class ConnectionHealthMonitor:
    """连接健康监控"""
    
    def __init__(self):
        self._domain_stats: Dict[str, Dict] = {}
    
    def record_request(self, domain: str, success: bool, duration: float):
        """记录请求统计"""
        if domain not in self._domain_stats:
            self._domain_stats[domain] = {
                'total_requests': 0,
                'successful_requests': 0,
                'total_duration': 0.0,
                'avg_duration': 0.0,
                'success_rate': 1.0
            }
        
        stats = self._domain_stats[domain]
        stats['total_requests'] += 1
        stats['total_duration'] += duration
        
        if success:
            stats['successful_requests'] += 1
        
        stats['avg_duration'] = stats['total_duration'] / stats['total_requests']
        stats['success_rate'] = stats['successful_requests'] / stats['total_requests']
    
    def get_domain_health(self, domain: str) -> Dict:
        """获取域名健康状态"""
        return self._domain_stats.get(domain, {
            'total_requests': 0,
            'successful_requests': 0,
            'avg_duration': 0.0,
            'success_rate': 1.0
        })
    
    def is_domain_healthy(self, domain: str, min_success_rate: float = 0.8) -> bool:
        """判断域名是否健康"""
        stats = self.get_domain_health(domain)
        return stats['success_rate'] >= min_success_rate


# 全局健康监控实例
health_monitor = ConnectionHealthMonitor()


def get_health_monitor() -> ConnectionHealthMonitor:
    """获取健康监控实例"""
    return health_monitor
