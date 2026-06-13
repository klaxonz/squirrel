from __future__ import annotations

from services.subscription.update.models import SyncCommand, UpdateMode, UpdateTrigger
from utils.trace import generate_trace_id, get_trace_id


def build_command(**kwargs) -> SyncCommand:
    mode = kwargs['mode']
    resolved_mode = UpdateMode.FULL if mode == UpdateMode.FULL else UpdateMode.INCREMENTAL
    return SyncCommand(
        **{
            **kwargs,
            'mode': resolved_mode,
            'trace_id': kwargs.get('trace_id') or get_trace_id() or generate_trace_id(),
        },
    )


def build_task_payload(
    command: SyncCommand,
    sync_state_id: int,
    queue_token: str,
    *,
    request_id: str | None,
    run_id: str,
) -> dict:
    return {
        'subscription_id': command.subscription_id,
        'url': command.url,
        'sync_state_id': sync_state_id,
        'mode': command.mode.value,
        'user_id': command.user_id,
        'force': command.force,
        'queue_token': queue_token,
        'trigger': command.trigger.value,
        'run_id': run_id,
        'trace_id': command.trace_id,
        'request_id': request_id,
    }


def resolve_priority(trigger: UpdateTrigger, mode: UpdateMode) -> str:
    if trigger == UpdateTrigger.MANUAL:
        return 'manual'
    if mode == UpdateMode.FULL:
        return 'full'
    return 'incr'
