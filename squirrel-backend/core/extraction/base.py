"""
数据提取基础实现类
"""
import logging
from typing import List
from urllib.parse import urlparse

from .interfaces import (
    IExtractor, ITaskProcessor, IResultHandler,
    ExtractionTask, ExtractionResult
)

logger = logging.getLogger(__name__)


class BaseExtractor(IExtractor):
    """基础提取器实现"""
    
    def __init__(self, site_name: str, supported_domains: List[str]):
        self.site_name = site_name
        self._supported_domains = supported_domains
    
    @property
    def supported_sites(self) -> List[str]:
        return [self.site_name]
    
    def can_handle(self, url: str) -> bool:
        """检查是否可以处理指定URL"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # 检查完整域名和父域名
            for supported_domain in self._supported_domains:
                if domain == supported_domain or domain.endswith(f'.{supported_domain}'):
                    return True
            return False
        except Exception as e:
            logger.warning(f"URL解析失败: {url}, error: {e}")
            return False
    
    def validate_url(self, url: str) -> bool:
        """验证URL格式"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    def extract(self, task: ExtractionTask) -> ExtractionResult:
        """基础提取实现，子类应重写此方法"""
        if not self.can_handle(task.url):
            return ExtractionResult(
                success=False,
                error=f"不支持的URL: {task.url}"
            )
        
        if not self.validate_url(task.url):
            return ExtractionResult(
                success=False,
                error=f"无效的URL格式: {task.url}"
            )
        
        # 子类应实现具体的提取逻辑
        return self._do_extract(task)
    
    def _do_extract(self, task: ExtractionTask) -> ExtractionResult:
        """具体的提取逻辑，子类必须实现"""
        raise NotImplementedError("子类必须实现_do_extract方法")


class BaseTaskProcessor(ITaskProcessor):
    """基础任务处理器"""
    
    def __init__(self, extractor: IExtractor, result_handler: IResultHandler):
        self.extractor = extractor
        self.result_handler = result_handler
    
    def can_process(self, task: ExtractionTask) -> bool:
        """检查是否可以处理任务"""
        return self.extractor.can_handle(task.url)
    
    def process(self, task: ExtractionTask) -> ExtractionResult:
        """处理任务"""
        try:
            logger.info(f"开始处理任务: {task.task_id}, URL: {task.url}")
            
            # 执行提取
            result = self.extractor.extract(task)
            
            # 处理结果
            if result.success:
                self.result_handler.handle_success(task, result)
                logger.info(f"任务处理成功: {task.task_id}")
            else:
                self.result_handler.handle_failure(task, result)
                logger.error(f"任务处理失败: {task.task_id}, error: {result.error}")
            
            return result
            
        except Exception as e:
            error_msg = f"任务处理异常: {task.task_id}, error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            result = ExtractionResult(
                success=False,
                error=error_msg
            )
            
            self.result_handler.handle_failure(task, result)
            return result


class BaseResultHandler(IResultHandler):
    """基础结果处理器"""
    
    def handle_success(self, task: ExtractionTask, result: ExtractionResult) -> None:
        """处理成功结果"""
        logger.info(f"任务成功: {task.task_id}")
        # 子类可以重写此方法实现具体的成功处理逻辑
    
    def handle_failure(self, task: ExtractionTask, result: ExtractionResult) -> None:
        """处理失败结果"""
        logger.error(f"任务失败: {task.task_id}, error: {result.error}")
        # 子类可以重写此方法实现具体的失败处理逻辑
