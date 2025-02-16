def get_videos_sql():
    return """
        select
            v.*,
            sp.id as subscription_id
        from subscription sp
        inner join user_subscription us on sp.id = us.subscription_id
        inner join subscription_video sv on sv.subscription_id = us.subscription_id
        inner join video v on sv.video_id = v.id
        /*{if category == 'read'}*/
            inner join video_history vh on vh.video_id = v.id and vh.user_id = :user_id
        /*{endif}*/
        /*{if category == 'unread'}*/
            left join video_history vh on vh.video_id = v.id and vh.user_id = :user_id
        /*{endif}*/
        where sp.is_deleted = 0 and us.is_deleted = 0 and v.is_deleted = 0
            and us.user_id = :user_id
        /*{if subscription_id}*/
            and sv.subscription_id = :subscription_id
        /*{endif}*/
        /*{if category == 'preview'}*/
            and v.publish_date > now()
        /*{endif}*/
        /*{if category != 'preview'}*/
            and v.publish_date <= now()
        /*{endif}*/
        /*{if category == 'unread'}*/
            and vh.video_id is null
        /*{endif}*/
        /*{if show_nsfw == False}*/
            and us.is_nsfw = 0
        /*{endif}*/
        /*{if query}*/
            and v.title like concat('%%', :query, '%%')
        /*{endif}*/
        /*{if sort_by == 'created_at'}*/
            order by v.created_at desc
        /*{endif}*/
        /*{if sort_by != 'created_at'}*/
            order by v.publish_date desc
        /*{endif}*/
        limit :limit offset :offset
    """


def count_videos_sql():
    return """
        select
            count(1) as total,
            count(IF(v.publish_date > now(), 1, NULL)) as preview,
            count(IF(vh.video_id IS NOT NULL, 1, NULL)) as `read`,
            count(IF(vh.video_id IS NULL, 1, NULL)) as unread
        from subscription sp
        inner join user_subscription us on sp.id = us.subscription_id
        inner join subscription_video sv on sv.subscription_id = us.subscription_id
        inner join video v on sv.video_id = v.id
        left join video_history vh 
            on vh.video_id = v.id 
            and vh.user_id = :user_id
        where sp.is_deleted = 0 
            and us.is_deleted = 0 
            and v.is_deleted = 0
            and us.user_id = :user_id
        /*{if subscription_id}*/
            and sv.subscription_id = :subscription_id
        /*{endif}*/
        /*{if query}*/
            and v.title like concat('%%', :query, '%%')
        /*{endif}*/
        /*{if show_nsfw == False}*/
            and us.is_nsfw = 0
        /*{endif}*/
    """
