"""
订阅更新编排器
统一入口，负责协调整个更新流程
"""
import logging
from utils import url_helper
from utils.metrics import metrics
from .models import SubscriptionUpdateRequest, SubscriptionUpdateResult
from .strategies.registry import StrategyRegistry
from .strategies.default_strategy import DefaultUpdateStrategy
from utils.site_catalog import SiteCatalog

logger = logging.getLogger(__name__)


class SubscriptionOrchestrator:
    """
    订阅更新编排器
    
    职责：
    1. 接收更新请求
    2. 选择合适的更新策略
    3. 执行更新流程
    4. 返回更新结果
    """
    
    def __init__(self):
        self.default_strategy = DefaultUpdateStrategy()
    
    def update(self, request: SubscriptionUpdateRequest) -> SubscriptionUpdateResult:
        """
        执行订阅更新
        
        Args:
            request: 更新请求
            
        Returns:
            更新结果
        """
        try:
            domain = url_helper.extract_top_level_domain(request.url)
            if not SiteCatalog.is_site_enabled(domain=domain):
                message = f"Site is disabled, skip subscription update: {domain}"
                logger.info(message)
                # 记录跳过指标
                metrics.counter("subscription.update.total", tags={"site": domain, "status": "skipped", "reason": "site_disabled"})
                return SubscriptionUpdateResult(
                    subscription_id=request.subscription_id,
                    success=False,
                    videos_found=0,
                    videos_enqueued=0,
                    error_message=message,
                    skipped_reason="site_disabled"
                )

            site_name = self._resolve_site(request.url)
            strategy = self._select_strategy(site_name)
            
            logger.debug(
                "Updating subscription %s using %s strategy (trigger=%s, mode=%s)",
                request.subscription_id,
                strategy.site_name,
                request.trigger.value,
                request.mode.value,
            )
            
            result = strategy.execute(request)
            
            return result
            
        except Exception as e:
            logger.error(f"Orchestrator error for subscription {request.subscription_id}: {e}", exc_info=True)
            
            return SubscriptionUpdateResult(
                subscription_id=request.subscription_id,
                success=False,
                videos_found=0,
                videos_enqueued=0,
                error_message=str(e)
            )
    
    def _resolve_site(self, url: str) -> str:
        """解析站点名称"""
        from crawl import get_extractor_registry
        
        domain = url_helper.extract_top_level_domain(url)
        
        # 检查是否有注册的提取器支持该域名
        extractor_registry = get_extractor_registry()
        site_key = extractor_registry.get_by_domain(domain)
        if site_key:
            return site_key
        
        return "default"
    
    def _select_strategy(self, site_name: str) -> 'UpdateStrategy':
        """选择更新策略"""
        strategy = StrategyRegistry.get_strategy(site_name)
        if strategy:
            logger.debug(f"Using {site_name} strategy")
            return strategy
        
        logger.debug(f"No specific strategy for {site_name}, using default")
        return self.default_strategy
    

orchestrator = SubscriptionOrchestrator()

