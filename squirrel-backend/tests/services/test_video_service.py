from domains.video.application.services.service import VideoService


def test_video_service_composes_shared_listing_dependencies(session_factory):
    first = VideoService(session_factory=session_factory)
    second = VideoService(session_factory=session_factory)

    assert first is not second
    assert first.thumbnail_downloader is not second.thumbnail_downloader
    assert first.listing._thumbnail_downloader is first.thumbnail_downloader
    assert first.featured._page_loader is first.listing._page_loader
    marker_serializer = first.listing._serialize_marker
    assert marker_serializer.__self__ is first.clip_marker
    assert marker_serializer.__func__ is first.clip_marker.serialize_marker.__func__

    first.close()
    second.close()
