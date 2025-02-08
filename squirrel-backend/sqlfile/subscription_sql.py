def get_subscriptions_sql():
    return """
        select 
            s.*,
            us.is_nsfw,
            coalesce(vc.video_count, 0) as total_extract
        from user_subscription us
        join subscription s on s.id = us.subscription_id
        left join (
            select 
                subscription_id,
                count(video_id) as video_count
            from subscription_video
            group by subscription_id
        ) vc on vc.subscription_id = s.id
        where us.is_deleted = 0
        and us.user_id = :user_id
        /*{if query}*/
        and (s.name like concat('%%', :query, '%%') 
             or s.description like concat('%%', :query, '%%'))
        /*{endif}*/
        /*{if type}*/
        and s.type = :type
        /*{endif}*/
        /*{if show_nsfw == False}*/
            and us.is_nsfw = 0
        /*{endif}*/
        order by s.created_at desc
        limit :limit offset :offset
    """


def get_subscriptions_count_sql():
    return """
        select count(*) as total
        from user_subscription us
        join subscription s on s.id = us.subscription_id
        where us.is_deleted = 0 
        and us.user_id = :user_id
        /*{if query}*/
        and (s.name like concat('%%', :query, '%%') 
             or s.description like concat('%%', :query, '%%'))
        /*{endif}*/
        /*{if type}*/
        and s.type = :type
        /*{endif}*/
        /*{if show_nsfw == False}*/
            and us.is_nsfw = 0
        /*{endif}*/
    """


def get_subscription_sql():
    return """
        select 
            s.*,
            0 as is_nsfw,
            coalesce(vc.video_count, 0) as total_extract
        from subscription s
        left join (
            select 
                subscription_id,
                count(video_id) as video_count
            from subscription_video
            group by subscription_id
        ) vc on vc.subscription_id = s.id
        where s.id = :subscription_id
    """
