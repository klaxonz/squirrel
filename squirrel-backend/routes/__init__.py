import importlib
import os
from pathlib import Path
from fastapi import APIRouter

router = APIRouter()

current_dir = Path(__file__).parent
route_files = [
    f[:-3] for f in os.listdir(current_dir) 
    if f.endswith('.py') 
    and f != '__init__.py'
    and f != 'base.py'
]

for route_file in route_files:
    module = importlib.import_module(f".{route_file}", package="routes")
    if hasattr(module, 'router'):
        router.include_router(module.router)
