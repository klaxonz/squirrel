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
    from mq.consumer_registrar import DomainConsumerRegistrar
    from consumer.processors.subscription_update_task import process_domain_subscription_update
    
    # 使用 register_with_stream_param 支持传递 queue_name 参数
    def handler_factory(queue_name: str):
        """创建包含 queue_name 的 handler"""
        def handler(message):
            return process_domain_subscription_update(message, queue_name)
        return handler
    
    count = DomainConsumerRegistrar.register_with_stream_param(
        queue_type=QueueType.SUBSCRIPTION_UPDATE,
        group='subscription_update_domain',
        consumer_prefix='subscription_update',
        handler_factory=handler_factory,
        block_ms=1000,
        read_count=1
    )
    return count


def setup_all_consumers():
    """
    配置所有域消费者
    应在消费者启动前调用
    """
    import logging
    logger = logging.getLogger()
    
    _setup_video_extract_consumer()
    
    # 订阅更新消费者直接注册（因为需要 queue_name 参数）
    count = _setup_subscription_update_consumer()
    logger.info(f"Registered {count} subscription update domain consumers")

