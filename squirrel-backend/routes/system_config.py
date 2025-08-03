import logging
from typing import Optional
from fastapi import APIRouter
from common.constants import SYS_ENABLE_SCHEDULER, SYS_ENABLE_WORKER
from controllers.scheduler_controller import scheduler_start, scheduler_stop
from controllers.worker_controller import worker_start, worker_stop
from fastapi import Body
from services.system_config_service import set_value
from core.database import get_session
from models.system_config import SystemConfig

router = APIRouter(prefix="/api/system/config", tags=["system-config"])
_logger = logging.getLogger(__name__)


def _apply_side_effects(new_enable_scheduler: Optional[bool], new_enable_worker: Optional[bool]) -> None:
    try:
        if new_enable_scheduler is not None:
            if new_enable_scheduler:
                scheduler_start()
            else:
                scheduler_stop()
    except Exception:
        _logger.exception("[system-config] apply scheduler change failed")

    try:
        if new_enable_worker is not None:
            if new_enable_worker:
                worker_start()
            else:
                worker_stop()
    except Exception:
        _logger.exception("[system-config] apply worker change failed")


@router.get("")
def get_system_config():
    """
    返回数据库中已有的所有系统配置（纯 KV，完全按照 DB 存储返回，不做硬编码和类型转换）。
    """
    with get_session() as session:
        rows = session.query(SystemConfig).all()
        return {row.key: row.value for row in rows}


@router.post("")
async def update_system_config(payload: dict = Body(...)):
    """
    通用更新接口：仅支持 JSON Body，逐项写入 system_config（纯字符串存储）。
    即时生效：只有当提交中包含 enable_scheduler/enable_worker 时才触发启停。
    返回：数据库中当前所有配置（纯 KV 字符串）
    """
    # 写入变更（通用 KV）
    for k, v in payload.items():
        set_value(k, str(v))

    def to_bool(val: Optional[str]) -> Optional[bool]:
        if val is None:
            return None
        s = str(val).strip().lower()
        if s in ("true", "1", "yes", "y", "on"):
            return True
        if s in ("false", "0", "no", "n", "off"):
            return False
        return None

    _apply_side_effects(
        to_bool(str(payload.get(SYS_ENABLE_SCHEDULER))) if SYS_ENABLE_SCHEDULER in payload else None,
        to_bool(str(payload.get(SYS_ENABLE_WORKER))) if SYS_ENABLE_WORKER in payload else None,
    )

    with get_session() as session:
        rows = session.query(SystemConfig).all()
        return {row.key: row.value for row in rows}
