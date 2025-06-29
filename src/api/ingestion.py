
from fastapi import APIRouter, Request, Depends, HTTPException, status, Query
from typing import Any, Optional

from ..services.alarm_lifecycle_manager import AlarmLifecycleManager
from ..adapters.factory import get_adapter
from ..core.auth import get_current_user # Assuming you have auth

router = APIRouter()

@router.post("/ingest")
async def unified_ingestion(
    request: Request,
    source: str = Query(..., description="The source system of the alarm (e.g., 'grafana', 'prometheus')"),
    token: Optional[str] = Query(None, description="Authentication token for the source, if required"),
    # current_user: dict = Depends(get_current_user) # Optional: secure the endpoint if needed
):
    """
    Unified endpoint for ingesting alarms from various sources.
    """
    adapter = get_adapter(source, token)
    if not adapter:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid source '{source}' specified."
        )

    try:
        payload = await request.json()
        standardized_alarms = await adapter.transform(payload)

        if not standardized_alarms:
            # This can happen if the payload is valid but contains no alarm data (e.g., a Grafana validation check)
            return {"status": "success", "message": "Payload received, but no alarms to process."}

        # Create alarms using the lifecycle manager
        created_alarms = await AlarmLifecycleManager.create_alarms(standardized_alarms)
        return {"status": "success", "data": created_alarms}

    except Exception as e:
        # Log the exception details for debugging
        # logger.error(f"Error processing ingestion from {source}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process data from source '{source}'. Reason: {str(e)}"
        )
