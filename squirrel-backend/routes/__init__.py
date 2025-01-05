import importlib
import os
from pathlib import Path

from routes.video import router as video_router
from routes.subscription import router as subscription_router
from routes.task import router as task_router

from routes.base import app

# current_dir = Path(__file__).parent
# route_files = [
#     f[:-3] for f in os.listdir(current_dir)
#     if f.endswith('.py')
#     and f != '__init__.py'
#     and f != 'base.py'
# ]
#
# for route_file in route_files:
#     module = importlib.import_module(f".{route_file}", package="routes")
#     if hasattr(module, 'router'):
#         app.include_router(module.router)

app.include_router(video_router)
app.include_router(task_router)
app.include_router(subscription_router)