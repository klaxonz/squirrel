def get_subscription_sql():
    return """
        select
            s.*,
            case
                when coalesce(vc.video_count, 0) > coalesce(s.total_videos, 0) then coalesce(vc.video_count, 0)
                else coalesce(s.total_videos, 0)
            end as total_videos,
            0 as is_nsfw,
            0 as is_special_followed,
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
