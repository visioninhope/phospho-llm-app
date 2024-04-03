from typing import List, Optional

from fastapi import APIRouter, Depends
from loguru import logger

from app.api.v2.models import (
    Project,
    ProjectUpdateRequest,
    ProjectTasksFilter,
    Sessions,
    Tasks,
    FlattenedTasks,
    FlattenedTasksRequest,
)

# from app.db.client import firestore_db as firestore_db
from app.security import authenticate_org_key, verify_propelauth_org_owns_project_id
from app.services.mongo.projects import (
    get_all_sessions,
    get_all_tasks,
    get_project_by_id,
    update_project,
)
from app.services.mongo.explore import (
    fetch_flattened_tasks,
    update_from_flattened_tasks,
)

router = APIRouter(tags=["Projects"])


@router.get(
    "/projects/{project_id}",
    response_model=Project,
    description="Get a specific project",
)
async def get_project(
    project_id: str,
    org: dict = Depends(authenticate_org_key),
) -> Project:
    """
    Get a specific project
    """
    await verify_propelauth_org_owns_project_id(org, project_id)
    project = await get_project_by_id(project_id)
    return project


@router.post(
    "/projects/{project_id}",
    response_model=Project,
    description="Update a project. Only the fields that are specified in the request will be updated. Filed specified will be overwritten (WARNING for nested fields like settings))",
)
async def post_update_project(
    project_id: str,
    project_update_request: ProjectUpdateRequest,
    org: dict = Depends(authenticate_org_key),
) -> Project:
    await verify_propelauth_org_owns_project_id(org, project_id)

    project = await get_project_by_id(project_id)

    updated_project = await update_project(
        project, **project_update_request.model_dump()
    )

    logger.debug(f"Project {project_id} updated successfully.")

    return updated_project


@router.get(
    "/projects/{project_id}/sessions",
    response_model=Sessions,
    description="Get all the sessions of a project",
)
async def get_sessions(
    project_id: str,
    limit: int = 1000,
    org: dict = Depends(authenticate_org_key),
):
    await verify_propelauth_org_owns_project_id(org, project_id)
    sessions = await get_all_sessions(project_id, limit)
    return Sessions(sessions=sessions)


@router.get(
    "/projects/{project_id}/tasks",
    response_model=Tasks,
    description="Get all the tasks of a project",
)
async def get_tasks(
    project_id: str,
    limit: int = 1000,
    task_filter: Optional[ProjectTasksFilter] = None,
    org: dict = Depends(authenticate_org_key),
) -> Tasks:
    """
    Get all the tasks of a project. If task_filter is specified, the tasks will be filtered according to the filter.

    Args:
        project_id: The id of the project
        limit: The maximum number of tasks to return
        task_filter: This model is used to filter tasks in the get_tasks endpoint. The filters are applied as AND filters.
    """
    await verify_propelauth_org_owns_project_id(org, project_id)
    if task_filter is None:
        task_filter = ProjectTasksFilter()
    if isinstance(task_filter.event_name, str):
        task_filter.event_name = [task_filter.event_name]

    tasks = await get_all_tasks(
        project_id=project_id,
        limit=limit,
        flag_filter=task_filter.flag,
        event_name_filter=task_filter.event_name,
        last_eval_source_filter=task_filter.last_eval_source,
        metadata_filter=task_filter.metadata,
    )
    return Tasks(tasks=tasks)


@router.post(
    "/projects/{project_id}/tasks/flat",
    response_model=FlattenedTasks,
    description="Get all the tasks of a project",
)
async def get_flattened_tasks(
    project_id: str,
    flattened_tasks_request: FlattenedTasksRequest,
    org: dict = Depends(authenticate_org_key),
) -> FlattenedTasks:
    """
    Get all the tasks of a project in a flattened format.

    Args:
        project_id: The id of the project
        limit: The maximum number of tasks to return
    """
    await verify_propelauth_org_owns_project_id(org, project_id)

    flattened_tasks = await fetch_flattened_tasks(
        project_id=project_id,
        limit=flattened_tasks_request.limit,
        with_events=flattened_tasks_request.with_events,
        with_sessions=flattened_tasks_request.with_sessions,
    )
    return FlattenedTasks(flattened_tasks=flattened_tasks)


@router.post(
    "/projects/{project_id}/tasks/flat-update",
    description="Update the tasks of a project using a flattened format",
)
async def post_flattened_tasks(
    project_id: str,
    flattened_tasks: FlattenedTasks,
    org: dict = Depends(authenticate_org_key),
) -> None:
    """
    Update the tasks of a project using a flattened format.
    """
    await verify_propelauth_org_owns_project_id(org, project_id)
    org_id = org["org"].get("org_id")

    await update_from_flattened_tasks(
        org_id=org_id,
        project_id=project_id,
        flattened_tasks=flattened_tasks.flattened_tasks,
    )
    return None
