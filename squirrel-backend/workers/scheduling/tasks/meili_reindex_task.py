"""定时全量重建 Meilisearch 视频索引（兜底增量直写的遗漏 + 首次回填）。"""
import logging

from domains.video.application.services.search.meili_indexer import get_meili_video_indexer
from infrastructure.config.settings import settings
from infrastructure.scheduling.base import BaseTask, TaskRegistry

logger = logging.getLogger(__name__)


@TaskRegistry.register(interval=24, unit="hours", start_immediately=False)
class MeiliReindexTask(BaseTask):
    """每 24 小时全量重建一次 Meilisearch 索引。

    全量重建数据量较大（当前约 60 万视频），不宜 start_immediately，
    首次回填请手动执行 reindex_all（见 scripts 或管理命令）。
    """

    @classmethod
    def run(cls):
        if not settings.meili.url:
            return
        try:
            count = get_meili_video_indexer().reindex_all()
            logger.info('MeiliReindexTask 完成，共 %d 个视频', count)
        except Exception as exc:  # task boundary — 防止单次失败影响调度器
            logger.error('MeiliReindexTask error: %s', exc, exc_info=True)

    @classmethod
    def shutdown(cls):
        logger.info('MeiliReindexTask shutdown')
