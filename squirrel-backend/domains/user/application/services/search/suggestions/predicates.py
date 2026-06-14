from typing import Any

from domains.subscription.domain.junctions.user_subscription import UserSubscription
from domains.subscription.domain.models.subscription import Subscription


def apply_nsfw_visibility(conditions: list[Any], effective_nsfw: str) -> list[Any]:
    """对基于 UserSubscription 的实时 join 查询追加 nsfw 可见性条件。"""
    if effective_nsfw == 'blocked':
        conditions.append(False)
    elif effective_nsfw == 'yes':
        conditions.append(UserSubscription.is_nsfw.is_(True))
    elif effective_nsfw == 'no':
        conditions.append(UserSubscription.is_nsfw.is_(False))
    return conditions


def subscription_visibility_predicates(user_id: int, effective_nsfw: str) -> list[Any]:
    """已订阅维度（UserSubscription × Subscription）的可见性谓词。

    用于 build_subscription_pool / build_video_pool 等 pool 查询的实时 join 路径。
    """
    predicates: list[Any] = [
        UserSubscription.user_id == user_id,
        UserSubscription.is_deleted.is_(False),
        Subscription.is_deleted.is_(False),
    ]
    apply_nsfw_visibility(predicates, effective_nsfw)
    return predicates
