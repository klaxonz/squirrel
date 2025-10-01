"""
消费者配置注册
集中管理所有域消费者的配置和 handler 映射
"""
from mq.consumer_config import ConsumerConfig, ConsumerConfigManager
from mq.queue_config import QueueType


def _setup_video_extract_consumer():
    """配置视频提取消费者"""
    from consumer.processors.extract_task import process_domain_video_extract
    
    config = ConsumerConfig(
        queue_type=QueueType.VIDEO_EXTRACT,
        group='extract-domain',
        consumer_prefix='extract',
        handler=process_domain_video_extract,
        block_ms=1000,
        read_count=1
    )
    ConsumerConfigManager.register_config(config)


def _setup_subscription_update_consumer():
    """配置订阅更新消费者（域级别队列）"""
    from consumer.processors.subscription_update_task import process_domain_subscription_update
    
    config = ConsumerConfig(
        queue_type=QueueType.SUBSCRIPTION_UPDATE,
        group='subscription_update_domain',
        consumer_prefix='subscription_update',
        handler=process_domain_subscription_update,
        block_ms=1000,
        read_count=1
    )
    ConsumerConfigManager.register_config(config)


def setup_all_consumers():
    """
    配置所有域消费者
    应在消费者启动前调用
    """
    _setup_video_extract_consumer()
    _setup_subscription_update_consumer()

