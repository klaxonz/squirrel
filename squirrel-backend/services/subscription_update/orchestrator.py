"""
订阅更新编排器
统一入口，负责协调整个更新流程
"""
import logging
from utils import url_helper
from .models import SubscriptionUpdateRequest, SubscriptionUpdateResult
from .strategies.registry import StrategyRegistry
from .strategies.default_strategy import DefaultUpdateStrategy
from core.progress import progress_emitter, ProgressEvent, ProgressEventType
from utils.site_catalog import SiteCatalog

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
            domain = url_helper.extract_top_level_domain(request.url)
            if not SiteCatalog.is_site_enabled(domain=domain):
                message = f"Site is disabled, skip subscription update: {domain}"
                logger.info(message)
                progress_emitter.emit(ProgressEvent(
                    event_type=ProgressEventType.SUBSCRIPTION_UPDATE_ERROR,
                    trace_id=request.trace_id,
                    subscription_id=request.subscription_id,
                    url=request.url,
                    error=message
                ))
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
            
            # 发射开始事件
            progress_emitter.emit(ProgressEvent(
                event_type=ProgressEventType.SUBSCRIPTION_UPDATE_START,
                trace_id=request.trace_id,
                subscription_id=request.subscription_id,
                url=request.url,
                message=f"Starting update with {strategy.site_name} strategy"
            ))
            
            logger.info(
                f"Updating subscription {request.subscription_id} "
                f"using {strategy.site_name} strategy "
                f"(trigger={request.trigger.value}, mode={request.mode.value})"
            )
            
            result = strategy.execute(request)
            
            # 发射完成事件
            if result.success:
                progress_emitter.emit(ProgressEvent(
                    event_type=ProgressEventType.SUBSCRIPTION_UPDATE_COMPLETE,
                    trace_id=request.trace_id,
                    subscription_id=request.subscription_id,
                    url=request.url,
                    current=result.videos_enqueued,
                    total=result.videos_found,
                    message=f"Updated successfully: {result.videos_enqueued}/{result.videos_found} videos"
                ))
            else:
                progress_emitter.emit(ProgressEvent(
                    event_type=ProgressEventType.SUBSCRIPTION_UPDATE_ERROR,
                    trace_id=request.trace_id,
                    subscription_id=request.subscription_id,
                    url=request.url,
                    error=result.error_message
                ))
            
            return result
            
        except Exception as e:
            logger.error(f"Orchestrator error for subscription {request.subscription_id}: {e}", exc_info=True)
            
            # 发射错误事件
            progress_emitter.emit(ProgressEvent(
                event_type=ProgressEventType.SUBSCRIPTION_UPDATE_ERROR,
                trace_id=request.trace_id,
                subscription_id=request.subscription_id,
                url=request.url,
                error=str(e)
            ))
            
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
    

orchestrator = SubscriptionOrchestrator()

