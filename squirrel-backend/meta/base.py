from abc import abstractmethod


class Video:
    """Base class for video metadata"""
    DOMAIN = None

    def __init__(self, url, base_info=None):
        self._url = url
        self._base_info = base_info or {}
        self._id = None
        self._title = None
        self._description = None
        self._tags = None
        self._duration = None
        self._thumbnail = None
        self._upload_date = None
        self._actors = []
        self._season = None

    @property
    def url(self):
        return self._url

    @property
    def title(self):
        if self._title is None:
            self._title = self._base_info.get("title")
        return self._title

    @property
    def description(self):
        if self._description is None:
            self._description = self._base_info.get("description")
        return self._description

    @property
    def thumbnail(self):
        if self._thumbnail is None:
            self._thumbnail = self._base_info.get("thumbnail")
        return self._thumbnail

    @property
    def upload_date(self):
        if self._upload_date is None:
            self._upload_date = self._base_info.get("upload_date")
        return self._upload_date

    @property
    def tags(self):
        if self._tags is None:
            self._tags = self._base_info.get("tags")
        return self._tags

    @property
    def duration(self):
        if self._duration is None:
            self._duration = self._base_info.get("duration")
        return self._duration

    @property
    def season(self):
        if self._season is None:
            self._season = self.upload_date[0:4]
        return self._season

    @property
    @abstractmethod
    def actors(self):
        """
        Abstract property that must be implemented by subclasses.
        Returns the actors configuration.
        """
        raise NotImplementedError("Subclasses must implement actors property")

    def video_exists(self):
        return True


class Actor:
    """Base class for channel/uploader metadata"""
    DOMAIN = None

    def __init__(self, url):
        self._url = url
        self._name = None
        self._avatar = None

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, value):
        self._url = value

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def avatar(self):
        return self._avatar

    @avatar.setter
    def avatar(self, value):
        self._avatar = value
