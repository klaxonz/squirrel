#!/usr/bin/env python3
"""Update import paths after DDD reorganization."""

import os
import re
from pathlib import Path

# Define import mappings
IMPORT_MAPPINGS = [
    # Shared kernel
    (r'from shared\.kernel\.db import', 'from shared_kernel.domain.base import'),
    (r'from shared\.kernel\.mixins import', 'from shared_kernel.domain.mixins import'),
    (r'from shared\.kernel\.response import', 'from shared_kernel.application.response import'),
    (r'from shared\.kernel\.log import', 'from shared_kernel.infrastructure.log import'),
    (r'from shared\.kernel\.trace import', 'from shared_kernel.infrastructure.trace import'),
    (r'from shared\.kernel\.rate_limiter import', 'from shared_kernel.infrastructure.rate_limiter import'),
    (r'from shared\.kernel\.sql_parser import', 'from shared_kernel.infrastructure.sql_parser import'),

    # Junctions - need more specific patterns
    (r'from shared\.kernel\.junctions import SubscriptionVideo',
     'from domains.video.domain.junctions.subscription_video import SubscriptionVideo'),
    (r'from shared\.kernel\.junctions import VideoCreator',
     'from domains.video.domain.junctions.video_creator import VideoCreator'),
    (r'from shared\.kernel\.junctions import UserSubscription',
     'from domains.subscription.domain.junctions.user_subscription import UserSubscription'),
    (r'from shared\.kernel\.junctions import',
     'from domains.video.domain.junctions import'),

    # Infrastructure - core
    (r'from core\.config import', 'from infrastructure.config.settings import'),
    (r'from core\.database import', 'from infrastructure.database.session import'),
    (r'from core\.cache import', 'from infrastructure.cache.redis_client import'),
    (r'from core\.redis_client import', 'from infrastructure.cache.redis_client import'),
    (r'from core\.site_config_manager import', 'from infrastructure.config.site_config_manager import'),
    (r'from core\.startup_dependencies import', 'from infrastructure.config.startup_dependencies import'),
    (r'from core\.database_upgrade import', 'from infrastructure.database.migrations import'),

    # Infrastructure - shared packages
    (r'from shared\.site_catalog\.', 'from infrastructure.site_catalog.'),
    (r'from shared\.auth\.', 'from infrastructure.auth.'),
    (r'from shared\.observability\.', 'from infrastructure.observability.'),
    (r'from shared\.search\.', 'from infrastructure.search.'),

    # Infrastructure - other
    (r'from site_runtimes\.', 'from infrastructure.site_runtimes.'),
    (r'from extraction\.', 'from infrastructure.extraction.'),

    # Messaging
    (r'from messaging\.framework\.', 'from infrastructure.messaging.framework.'),
    (r'from messaging\.models\.', 'from infrastructure.messaging.models.'),
    (r'from messaging\.handlers\.', 'from workers.messaging.handlers.'),
    (r'from messaging\.process import', 'from workers.messaging.process import'),
    (r'from messaging\.worker import', 'from workers.messaging.worker import'),

    # Scheduling infrastructure
    (r'from scheduling\.base import', 'from infrastructure.scheduling.base import'),
    (r'from scheduling\.engine import', 'from infrastructure.scheduling.engine import'),
    (r'from scheduling\.lifecycle import', 'from infrastructure.scheduling.lifecycle import'),
    (r'from scheduling\.factory import', 'from infrastructure.scheduling.factory import'),
    (r'from scheduling\.store import', 'from infrastructure.scheduling.store import'),
    (r'from scheduling\.sync import', 'from infrastructure.scheduling.sync import'),
    (r'from scheduling\.bootstrap import', 'from infrastructure.scheduling.bootstrap import'),
    (r'from scheduling\.service import', 'from infrastructure.scheduling.service import'),
    (r'from scheduling\.models\.', 'from infrastructure.scheduling.models.'),
    (r'from scheduling\.routes import', 'from infrastructure.scheduling.routes import'),

    # Scheduling workers/tasks
    (r'from scheduling\.tasks\.', 'from workers.scheduling.tasks.'),
    (r'from scheduling\.workers\.', 'from workers.scheduling.workers.'),
    (r'from scheduling\.process import', 'from workers.scheduling.process import'),

    # Routes
    (r'from routes\.base import', 'from application.app import'),
    (r'from routes\.health import', 'from application.routes.health import'),
    (r'from routes\.logs import', 'from application.routes.logs import'),
    (r'from routes\.middleware\.', 'from infrastructure.http.middleware.'),

    # Runtime
    (r'from runtime\.bootstrap import', 'from application.lifespan import'),
]

# Domain mappings - these need to be more careful
DOMAIN_MAPPINGS = [
    # Video domain
    (r'from video\.models\.', 'from domains.video.domain.models.'),
    (r'from video\.services\.', 'from domains.video.application.services.'),
    (r'from video\.routes\.', 'from domains.video.interfaces.http.'),
    (r'from video\.schemas\.', 'from domains.video.interfaces.dto.'),

    # Subscription domain
    (r'from subscription\.models\.', 'from domains.subscription.domain.models.'),
    (r'from subscription\.services\.', 'from domains.subscription.application.services.'),
    (r'from subscription\.routes\.', 'from domains.subscription.interfaces.http.'),
    (r'from subscription\.schemas\.', 'from domains.subscription.interfaces.dto.'),
    (r'from subscription\.constants import', 'from domains.subscription.constants import'),

    # User domain
    (r'from user\.models\.', 'from domains.user.domain.models.'),
    (r'from user\.services\.', 'from domains.user.application.services.'),
    (r'from user\.routes\.', 'from domains.user.interfaces.http.'),
    (r'from user\.schemas\.', 'from domains.user.interfaces.dto.'),

    # Playlist domain
    (r'from playlist\.models\.', 'from domains.playlist.domain.models.'),
    (r'from playlist\.services\.', 'from domains.playlist.application.services.'),
    (r'from playlist\.routes\.', 'from domains.playlist.interfaces.http.'),
    (r'from playlist\.schemas\.', 'from domains.playlist.interfaces.dto.'),

    # RSS domain
    (r'from rss\.models\.', 'from domains.rss.domain.models.'),
    (r'from rss\.services\.', 'from domains.rss.application.services.'),
    (r'from rss\.routes\.', 'from domains.rss.interfaces.http.'),

    # Music domain
    (r'from music\.services\.', 'from domains.music.application.services.'),
    (r'from music\.routes\.', 'from domains.music.interfaces.http.'),
    (r'from music\.schemas\.', 'from domains.music.interfaces.dto.'),
]


def update_file(file_path: Path) -> bool:
    """Update imports in a single file. Returns True if file was modified."""
    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception:
        return False

    original = content

    # Apply all mappings
    all_mappings = IMPORT_MAPPINGS + DOMAIN_MAPPINGS
    for pattern, replacement in all_mappings:
        content = re.sub(pattern, replacement, content)

    if content != original:
        file_path.write_text(content, encoding='utf-8')
        return True
    return False


def main():
    # Directories to process
    directories = [
        'domains',
        'infrastructure',
        'workers',
        'application',
        'shared_kernel',
    ]

    count = 0
    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            continue

        for py_file in dir_path.rglob('*.py'):
            if update_file(py_file):
                count += 1
                print(f"Updated: {py_file}")

    print(f"\nTotal files updated: {count}")


if __name__ == '__main__':
    main()
