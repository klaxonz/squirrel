from pathlib import Path
import sys

from sqlalchemy.orm import configure_mappers

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import models.creator  # noqa: F401
import models.links  # noqa: F401
import models.playlist  # noqa: F401
import models.playlist_item  # noqa: F401
import models.subscription  # noqa: F401
import models.video  # noqa: F401
import models.video_clip_marker  # noqa: F401
import models.video_history  # noqa: F401
import models.video_interaction  # noqa: F401
from models.playlist import Playlist
from models.playlist_item import PlaylistItem


def test_playlist_items_relationship_configures_without_foreign_keys():
    configure_mappers()

    relationship = Playlist.__mapper__.relationships['items']

    assert relationship.mapper.class_ is PlaylistItem
    assert str(relationship.primaryjoin) == 'playlist.id = playlist_item.playlist_id'
