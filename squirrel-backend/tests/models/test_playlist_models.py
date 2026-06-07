import sys
from pathlib import Path

from sqlalchemy.orm import configure_mappers

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import models.creator
import models.links
import models.playlist
import models.playlist_item
import models.subscription
import models.video
import models.video_clip_marker
import models.video_history
import models.video_interaction  # noqa: F401
from models.playlist import Playlist
from models.playlist_item import PlaylistItem


def test_playlist_items_relationship_configures_without_foreign_keys():
    configure_mappers()

    relationship = Playlist.__mapper__.relationships["items"]

    assert relationship.mapper.class_ is PlaylistItem
    assert str(relationship.primaryjoin) == "playlist.id = playlist_item.playlist_id"
