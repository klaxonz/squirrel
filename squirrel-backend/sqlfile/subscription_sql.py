def get_subscriptions_sql():
    return """
        select 
            s.*,
            us.is_nsfw,
            coalesce(vc.video_count, 0) as total_extract,
            coalesce(ss.sync_status, 'idle') as sync_status,
            ss.last_sync_at,
            ss.last_success_at,
            ss.next_sync_at,
            ss.last_error,
            coalesce(ss.pending_video_count, 0) as pending_video_count
        from user_subscription us
        join subscription s on s.id = us.subscription_id
        left join subscription_sync_state ss
            on ss.subscription_id = s.id
            and ss.sync_mode = 'incremental'
        left join (
            select 
                subscription_id,
                count(video_id) as video_count
            from subscription_video
            group by subscription_id
        ) vc on vc.subscription_id = s.id
        where us.is_deleted is false
        and us.user_id = :user_id
        /*{if query}*/
        and (s.name like concat('%%', :query, '%%') 
             or s.description like concat('%%', :query, '%%'))
        /*{endif}*/
        /*{if type}*/
        and s.type = :type
        /*{endif}*/
        /*{if nsfw == 'yes'}*/
            and us.is_nsfw is true
        /*{endif}*/
        /*{if nsfw == 'no'}*/
            and us.is_nsfw is false
        /*{endif}*/
        /*{if filter_nsfw_when_all}*/
            and us.is_nsfw is false
        /*{endif}*/
        order by s.created_at desc
        limit :limit offset :offset
    """


def get_subscriptions_count_sql():
    return """
        select count(*) as total
        from user_subscription us
        join subscription s on s.id = us.subscription_id
        where us.is_deleted is false
        and us.user_id = :user_id
        /*{if query}*/
        and (s.name like concat('%%', :query, '%%') 
             or s.description like concat('%%', :query, '%%'))
        /*{endif}*/
        /*{if type}*/
        and s.type = :type
        /*{endif}*/
        /*{if nsfw == 'yes'}*/
            and us.is_nsfw is true
        /*{endif}*/
        /*{if nsfw == 'no'}*/
            and us.is_nsfw is false
        /*{endif}*/
        /*{if filter_nsfw_when_all}*/
            and us.is_nsfw is false
        /*{endif}*/
    """


def get_subscription_sql():
    return """
        select 
            s.*,
            0 as is_nsfw,
            coalesce(vc.video_count, 0) as total_extract,
            coalesce(ss.sync_status, 'idle') as sync_status,
            ss.last_sync_at,
            ss.last_success_at,
            ss.next_sync_at,
            ss.last_error,
            coalesce(ss.pending_video_count, 0) as pending_video_count
        from subscription s
        left join subscription_sync_state ss
            on ss.subscription_id = s.id
            and ss.sync_mode = 'incremental'
        left join (
            select 
                subscription_id,
                count(video_id) as video_count
            from subscription_video
            group by subscription_id
        ) vc on vc.subscription_id = s.id
        where s.id = :subscription_id
    """
