class ConsumerRegistry:
    consumers = []

    @classmethod
    def register(cls, queue_name: str, num_threads: int = 1):
        def decorator(consumer_class):
            consumer_class.queue_name = queue_name
            consumer_class.num_threads = num_threads
            cls.consumers.append(consumer_class)
            return consumer_class

        return decorator

    @classmethod
    def get_consumers(cls):
        return cls.consumers
