from abc import ABC, abstractmethod
from typing import Dict, Type
from fastapi import Request, HTTPException
from starlette.responses import StreamingResponse
import logging

from schemas.proxy import VideoProxyRequest
from proxy.bilibili import BilibiliProxy
from proxy.javdb import JavdbProxy
from proxy.pornhub import PornhubProxy
from proxy.video_proxy import VideoProxy
from services.proxy_config_service import ProxyConfigFactory
from exceptions.proxy_exceptions import UnsupportedDomainException, ProxyException

logger = logging.getLogger(__name__)


class ProxyServiceInterface(ABC):
    """代理服务接口"""
    
    @abstractmethod
    async def handle_proxy_request(self, request: VideoProxyRequest, http_request: Request) -> StreamingResponse:
        """处理代理请求"""
        pass


class VideoProxyService(ProxyServiceInterface):
    """视频代理服务实现"""

    def __init__(self):
        self._proxy_registry: Dict[str, Type[VideoProxy]] = {
            "bilibili.com": BilibiliProxy,
            "javdb.com": JavdbProxy,
            "pornhub.com": PornhubProxy
        }
        self._config_service = ProxyConfigFactory.get_config_service()
    
    def _get_proxy_class(self, domain: str) -> Type[VideoProxy]:
        """根据域名获取代理类"""
        proxy_class = self._proxy_registry.get(domain)
        if not proxy_class:
            raise UnsupportedDomainException(domain)
        return proxy_class
    
    def _create_proxy_instance(self, proxy_class: Type[VideoProxy], http_request: Request) -> VideoProxy:
        """创建代理实例"""
        return proxy_class(http_request)
    
    async def handle_proxy_request(self, request: VideoProxyRequest, http_request: Request) -> StreamingResponse:
        """处理代理请求"""
        try:
            logger.debug(f"Processing proxy request for domain: {request.domain}, url: {request.url}")

            proxy_class = self._get_proxy_class(request.domain)
            proxy_instance = self._create_proxy_instance(proxy_class, http_request)

            # 获取域名配置（如果需要的话，可以用于后续优化）
            config = self._config_service.get_config(request.domain)
            if config:
                logger.debug(f"Using config for {request.domain}: timeout={config.timeout}, chunk_size={config.chunk_size}")

            return await proxy_instance.handle_stream(request.url)
        except ProxyException as e:
            logger.warning(f"Proxy exception for domain {request.domain}: {e.message}")
            raise HTTPException(status_code=e.status_code, detail=e.message)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected proxy error for domain {request.domain}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"代理请求处理失败: {str(e)}"
            )
    
    def get_supported_domains(self) -> list[str]:
        """获取支持的域名列表"""
        return list(self._proxy_registry.keys())
    
    def is_domain_supported(self, domain: str) -> bool:
        """检查域名是否支持"""
        return domain in self._proxy_registry

    async def get_proxy_health_status(self) -> Dict[str, bool]:
        """获取所有代理的健康状态"""
        health_status = {}
        for domain in self._proxy_registry.keys():
            try:
                # 这里可以添加实际的健康检查逻辑
                # 目前简单返回 True，表示服务可用
                health_status[domain] = True
            except Exception as e:
                logger.warning(f"Health check failed for {domain}: {str(e)}")
                health_status[domain] = False
        return health_status


class ProxyServiceFactory:
    """代理服务工厂"""
    
    _instance: VideoProxyService = None
    
    @classmethod
    def get_proxy_service(cls) -> VideoProxyService:
        """获取代理服务实例（单例模式）"""
        if cls._instance is None:
            cls._instance = VideoProxyService()
        return cls._instance
