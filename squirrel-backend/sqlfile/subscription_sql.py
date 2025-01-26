def get_subscriptions_sql():
    return """
        select 
            s.*,
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
        where us.user_id = :user_id
        /*{if query}*/
        and (s.name like concat('%%', :query, '%%') 
             or s.description like concat('%%', :query, '%%'))
        /*{endif}*/
        /*{if type}*/
        and s.type = :type
        /*{endif}*/
        order by s.created_at desc
    """


def get_subscriptions_count_sql():
    return """
        select count(*) as total
        from user_subscription us
        join subscription s on s.id = us.subscription_id
        where us.user_id = :user_id
        /*{if query}*/
        and (s.name like concat('%%', :query, '%%') 
             or s.description like concat('%%', :query, '%%'))
        /*{endif}*/
        /*{if type}*/
        and s.type = :type
        /*{endif}*/
    """
