"""
订阅更新编排器
统一入口，负责协调整个更新流程
"""
import logging
from utils import url_helper
from .models import SubscriptionUpdateRequest, SubscriptionUpdateResult
from .strategies.registry import StrategyRegistry
from .strategies.default_strategy import DefaultUpdateStrategy

logger = logging.getLogger()


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
            site_name = self._resolve_site(request.url)
            
            strategy = self._select_strategy(site_name)
            
            logger.info(
                f"Updating subscription {request.subscription_id} "
                f"using {strategy.site_name} strategy "
                f"(trigger={request.trigger.value}, mode={request.mode.value})"
            )
            
            result = strategy.execute(request)
            
            self._log_result(result)
            
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
        from crawl import MetaRegistry
        
        domain = url_helper.extract_top_level_domain(url)
        
        # 检查是否有注册的插件支持该域名
        if MetaRegistry.get_meta_class(domain):
            # 从域名提取站点名称 (如 'bilibili.com' -> 'bilibili')
            return domain.split('.')[0] if '.' in domain else domain
        
        return "default"
    
    def _select_strategy(self, site_name: str) -> 'UpdateStrategy':
        """选择更新策略"""
        strategy = StrategyRegistry.get_strategy(site_name)
        if strategy:
            logger.debug(f"Using {site_name} strategy")
            return strategy
        
        logger.debug(f"No specific strategy for {site_name}, using default")
        return self.default_strategy
    
    def _log_result(self, result: SubscriptionUpdateResult):
        """记录更新结果"""
        if result.success:
            if result.skipped_reason:
                logger.info(
                    f"Subscription {result.subscription_id} skipped: {result.skipped_reason}"
                )
            else:
                logger.info(
                    f"Subscription {result.subscription_id} updated: "
                    f"found={result.videos_found}, enqueued={result.videos_enqueued}"
                )
        else:
            logger.error(
                f"Subscription {result.subscription_id} update failed: {result.error_message}"
            )


orchestrator = SubscriptionOrchestrator()

