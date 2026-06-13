from typing import Any

from domains.subscription.domain.junctions.user_subscription import UserSubscription
from domains.subscription.domain.models.subscription import Subscription
from domains.user.domain.models.user_video_feed import UserVideoFeed


def apply_nsfw_visibility(conditions: list[Any], effective_nsfw: str) -> list[Any]:
    if effective_nsfw == 'blocked':
        conditions.append(False)
    elif effective_nsfw == 'yes':
        conditions.append(UserSubscription.is_nsfw.is_(True))
    elif effective_nsfw == 'no':
        conditions.append(UserSubscription.is_nsfw.is_(False))
    return conditions


def feed_visibility_predicates(user_id: int, effective_nsfw: str) -> list[Any]:
    predicates: list[Any] = [UserVideoFeed.user_id == user_id]
    if effective_nsfw == 'blocked':
        predicates.append(False)
    elif effective_nsfw == 'yes':
        predicates.append(UserVideoFeed.is_nsfw.is_(True))
    elif effective_nsfw == 'no':
        predicates.append(UserVideoFeed.is_nsfw.is_(False))
    return predicates


def subscription_visibility_predicates(user_id: int, effective_nsfw: str) -> list[Any]:
    predicates: list[Any] = [
        UserSubscription.user_id == user_id,
        UserSubscription.is_deleted.is_(False),
        Subscription.is_deleted.is_(False),
    ]
    apply_nsfw_visibility(predicates, effective_nsfw)
    return predicates

