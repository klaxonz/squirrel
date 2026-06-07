INCREMENTAL_SUBSCRIPTION_SYNC_TASK_TYPE = "subscription_sync_incremental"
FULL_SUBSCRIPTION_SYNC_TASK_TYPE = "subscription_sync_full"
LEGACY_SUBSCRIPTION_SYNC_TASK_TYPE = "subscription_sync"


class TaskTypes:
    @staticmethod
    def resolve_subscription_sync_task_type(mode: str | None) -> str:
        if str(mode or "").lower() == "full":
            return FULL_SUBSCRIPTION_SYNC_TASK_TYPE
        return INCREMENTAL_SUBSCRIPTION_SYNC_TASK_TYPE

    @staticmethod
    def subscription_sync_task_types() -> tuple[str, ...]:
        return (
            LEGACY_SUBSCRIPTION_SYNC_TASK_TYPE,
            INCREMENTAL_SUBSCRIPTION_SYNC_TASK_TYPE,
            FULL_SUBSCRIPTION_SYNC_TASK_TYPE,
        )

    @staticmethod
    def is_subscription_sync_task_type(task_type: str | None) -> bool:
        return str(task_type or "") in TaskTypes.subscription_sync_task_types()


_default = TaskTypes()
resolve_subscription_sync_task_type = _default.resolve_subscription_sync_task_type
subscription_sync_task_types = _default.subscription_sync_task_types
is_subscription_sync_task_type = _default.is_subscription_sync_task_type
