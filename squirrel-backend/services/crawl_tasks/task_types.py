INCREMENTAL_SUBSCRIPTION_SYNC_TASK_TYPE = 'subscription_sync_incremental'
FULL_SUBSCRIPTION_SYNC_TASK_TYPE = 'subscription_sync_full'


def resolve_subscription_sync_task_type(mode: str | None) -> str:
    if str(mode or '').lower() == 'full':
        return FULL_SUBSCRIPTION_SYNC_TASK_TYPE
    return INCREMENTAL_SUBSCRIPTION_SYNC_TASK_TYPE


def subscription_sync_task_types() -> tuple[str, str]:
    return (
        INCREMENTAL_SUBSCRIPTION_SYNC_TASK_TYPE,
        FULL_SUBSCRIPTION_SYNC_TASK_TYPE,
    )


def is_subscription_sync_task_type(task_type: str | None) -> bool:
    return str(task_type or '') in subscription_sync_task_types()
