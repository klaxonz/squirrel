from typing import Optional, Tuple, List, Dict, Any

from sqlmodel import select, or_, and_, func

from core.database import get_session
from models.links import SubscriptionVideo
from models.subscription import Subscription


class SubscriptionService:

    def list_subscriptions(
            self,
            query: Optional[str],
            content_type: Optional[str],
            status: Optional[str],
            page: int,
            page_size: int
    ) -> Tuple[List[Dict[str, Any]], int]:
        """获取订阅列表"""
        with get_session() as session:
            # 使用子查询统计每个订阅的视频数量
            video_count_subquery = (
                select(
                    SubscriptionVideo.subscription_id,
                    func.count(SubscriptionVideo.video_id).label("video_count")
                )
                .group_by(SubscriptionVideo.subscription_id)
                .subquery()
            )

            # 主查询
            statement = (
                select(
                    Subscription,
                    func.coalesce(video_count_subquery.c.video_count, 0).label("video_count")
                )
                .outerjoin(
                    video_count_subquery,
                    Subscription.subscription_id == video_count_subquery.c.subscription_id
                )
                .where(Subscription.is_deleted == 0)
            )

            # 添加过滤条件
            filters = []
            if query:
                filters.append(
                    or_(
                        Subscription.content_name.contains(query),
                        Subscription.description.contains(query)
                    )
                )
            if content_type:
                filters.append(Subscription.content_type == content_type)
            if status:
                filters.append(Subscription.status == status)

            if filters:
                statement = statement.where(and_(*filters))

            # 添加排序：按创建时间倒序
            statement = statement.order_by(Subscription.created_at.desc())

            # 计算总数
            total = session.exec(
                select(Subscription.subscription_id)
                .where(Subscription.is_deleted == 0)
                .where(*filters)
            ).all()
            total_count = len(total)

            # 分页
            statement = statement.offset((page - 1) * page_size).limit(page_size)

            # 执行查询
            results = session.exec(statement).all()

            # 处理结果
            subscriptions = []
            for result in results:
                subscription_dict = result[0].dict()
                subscription_dict["total_extract"] = result[1]
                subscriptions.append(subscription_dict)

            return subscriptions, total_count

    def get_subscription_detail(self, subscription_id: int) -> Optional[Dict[str, Any]]:
        """获取订阅详情"""
        with get_session() as session:
            subscription = session.get(Subscription, subscription_id)
            return subscription.dict() if subscription else None

    def update_subscription(
            self,
            subscription_id: int,
            update_data: Dict[str, Any]
    ) -> bool:
        """更新订阅信息"""
        with get_session() as session:
            subscription = session.get(Subscription, subscription_id)
            if not subscription:
                return False

            for key, value in update_data.items():
                if hasattr(subscription, key):
                    setattr(subscription, key, value)

            session.add(subscription)
            session.commit()
            return True

    def toggle_status(self, subscription_id: int, status: bool, field: str) -> bool:
        """切换订阅状态"""
        with get_session() as session:
            subscription = session.get(Subscription, subscription_id)
            if not subscription:
                return False

            try:
                setattr(subscription, field, status)
                session.add(subscription)
                session.commit()
                return True
            except ValueError:
                return False
