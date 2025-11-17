"""Node status and health check endpoints."""

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.database.connection import get_db
from src.shared.database.models import NodeState, PendingSubmission
from src.shared.models.schemas import NodeStatus
from src.shared.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["status"])

# Track when server started (for uptime calculation)
SERVER_START_TIME = datetime.utcnow()


@router.get("/health")
async def health_check() -> dict:
    """
    Basic health check endpoint.

    Returns:
        Status indicator
    """
    return {"status": "healthy"}


@router.get("/api/v1/status", response_model=NodeStatus)
async def get_node_status(
    db: AsyncSession = Depends(get_db),
) -> NodeStatus:
    """
    Get comprehensive node status and statistics.

    Args:
        db: Database session

    Returns:
        Node status including block height, pending submissions, etc.
    """
    # Get node state
    stmt = select(NodeState).where(NodeState.id == 1)
    result = await db.execute(stmt)
    state = result.scalar_one_or_none()

    block_height = state.current_block_height if state else 0
    total_hashes = state.total_hashes if state else 0
    last_block_time = state.last_block_time if state else None

    # Count pending submissions
    stmt = select(func.count(PendingSubmission.id)).where(
        PendingSubmission.batched == False  # noqa: E712
    )
    result = await db.execute(stmt)
    pending_count = result.scalar_one()

    # Calculate uptime
    uptime_seconds = (datetime.utcnow() - SERVER_START_TIME).total_seconds()
    uptime_str = str(timedelta(seconds=int(uptime_seconds)))

    # Get validator count
    validator_count = 1  # Phase 1: always 1
    if settings.consensus_mode == "poa":
        validator_count = len(settings.validator_nodes_list)

    return NodeStatus(
        node_id=settings.node_id,
        block_height=block_height,
        total_hashes=total_hashes,
        pending_submissions=pending_count,
        last_block_time=last_block_time.isoformat() if last_block_time else None,
        validator_nodes=validator_count,
        consensus_mode=settings.consensus_mode,
        uptime=uptime_str,
    )
