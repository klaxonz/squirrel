class VideoUrlHandlerError(Exception):
    pass


class UnsupportedDomainError(VideoUrlHandlerError):
    pass


class VideoUrlExtractionError(VideoUrlHandlerError):
    pass