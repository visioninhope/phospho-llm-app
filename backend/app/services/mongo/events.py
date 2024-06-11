from typing import Dict, List, Optional

from app.api.platform.models import EventBackfillRequest
from app.api.platform.models.explore import Pagination
from app.db.models import EventDefinition, Recipe
from app.db.mongo import get_mongo_db
from app.services.mongo.extractor import run_recipe_on_tasks
from app.services.mongo.recipe import run_recipe_on_tasks_batched
from app.services.mongo.tasks import get_all_tasks
from app.services.mongo.tasks import get_total_nb_of_tasks
from app.utils import cast_datetime_or_timestamp_to_timestamp
from fastapi import HTTPException
from loguru import logger

from phospho.models import Event, ProjectDataFilters


async def get_event_definition_from_event_id(
    project_id: str, event_id: str
) -> EventDefinition:
    """
    Utility function to get an EventDefinition in project settings from a given event_id
    """
    mongo_db = await get_mongo_db()
    event_definition = (
        await mongo_db["projects"]
        .aggregate(
            [
                {"$match": {"id": project_id}},
                {"$project": {"events": {"$objectToArray": "$$ROOT.settings.events"}}},
                {"$unwind": "$events"},
                # Use $filter to get the event definition from the array of events
                {"$match": {"events.v.id": event_id}},
                {"$project": {"events": "$events.v"}},
                {"$replaceRoot": {"newRoot": "$events"}},
            ]
        )
        .to_list(1)
    )
    if not event_definition:
        raise HTTPException(status_code=404, detail="Event definition not found")
    try:
        validated_event = EventDefinition.model_validate(event_definition[0])
        return validated_event
    except Exception as e:
        logger.error(f"Error validating event: {e}")
        raise HTTPException(status_code=500, detail="Error validating event")


async def get_event_from_name_and_project_id(
    project_id: str, event_name: str
) -> EventDefinition:
    """
    Utility function to get an event from a given project_id and event_name
    """

    mongo_db = await get_mongo_db()
    event_definition = (
        await mongo_db["projects"]
        .aggregate(
            [
                {"$match": {"id": project_id}},
                {"$project": {"events": {"$objectToArray": "$$ROOT.settings.events"}}},
                {"$unwind": "$events"},
                # Use $filter to get the event definition from the array of events
                {"$match": {"events.v.name": event_name}},
                {"$project": {"events": "$events.v"}},
                {"$replaceRoot": {"newRoot": "$events"}},
            ]
        )
        .to_list(1)
    )
    if not event_definition:
        raise HTTPException(status_code=404, detail="Event definition not found")
    validated_event = EventDefinition.model_validate(event_definition[0])
    return validated_event


async def run_event_detection_on_timeframe(
    org_id: str, project_id: str, event_backfill_request: EventBackfillRequest
) -> None:
    """
    Run event detection on a given event_id and event_data
    """
    event_definition = await get_event_definition_from_event_id(
        project_id, event_backfill_request.event_id
    )
    if event_definition.recipe_id is None:
        logger.error(
            f"Event {event_definition.event_name} has no recipe_id for project {project_id}. Canceling."
        )
        return
    if event_backfill_request.created_at_end is not None:
        event_backfill_request.created_at_end = round(
            event_backfill_request.created_at_end
        )
    if event_backfill_request.created_at_start is not None:
        event_backfill_request.created_at_start = round(
            event_backfill_request.created_at_start
        )
    filters = ProjectDataFilters(
        created_at_start=event_backfill_request.created_at_start,
        created_at_end=event_backfill_request.created_at_end,
    )
    await run_recipe_on_tasks_batched(
        project_id=project_id,
        recipe_id=event_definition.recipe_id,
        org_id=org_id,
        filters=filters,
        sample_rate=event_backfill_request.sample_rate,
    )

    return None


async def get_all_events(
    project_id: str,
    limit: Optional[int] = None,
    filters: Optional[ProjectDataFilters] = None,
    include_removed: bool = False,
    unique: bool = False,
) -> List[Event]:
    mongo_db = await get_mongo_db()
    additional_event_filters: Dict[str, object] = {}
    pipeline: List[Dict[str, object]] = []
    if filters is not None:
        if filters.event_name is not None:
            if isinstance(filters.event_name, str):
                additional_event_filters["event_name"] = filters.event_name
            if isinstance(filters.event_name, list):
                additional_event_filters["event_name"] = {"$in": filters.event_name}
        if filters.created_at_start is not None:
            additional_event_filters["created_at"] = {
                "$gt": cast_datetime_or_timestamp_to_timestamp(filters.created_at_start)
            }
        if filters.created_at_end is not None:
            additional_event_filters["created_at"] = {
                **additional_event_filters.get("created_at", {}),
                "$lt": cast_datetime_or_timestamp_to_timestamp(filters.created_at_end),
            }
    if not include_removed:
        additional_event_filters["removed"] = {"$ne": True}

    pipeline.append(
        {
            "$match": {
                "project_id": project_id,
                **additional_event_filters,
            }
        }
    )

    if unique:
        # Deduplicate the events based on event name
        pipeline.extend(
            [
                {
                    "$group": {
                        "_id": "$event_name",
                        "doc": {"$first": "$$ROOT"},
                    }
                },
                {"$replaceRoot": {"newRoot": "$doc"}},
            ]
        )

    pipeline.append({"$sort": {"created_at": -1}})

    events = await mongo_db["events"].aggregate(pipeline).to_list(length=limit)

    # Cast to model
    events = [Event.model_validate(data) for data in events]
    return events


async def confirm_event(
    project_id: str,
    event_id: str,
    event_source: str = "owner",
) -> Event:
    mongo_db = await get_mongo_db()
    # Get the event
    event = await mongo_db["events"].find_one(
        {"project_id": project_id, "id": event_id}
    )
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    event_model = Event.model_validate(event)

    # Edit the event. Note: this always confirm the event.
    result = await mongo_db["events"].update_one(
        {"project_id": project_id, "id": event_id},
        {"$set": {"confirmed": True}},
    )

    event_model.confirmed = True

    return event_model
