from loguru import logger
from app.db.mongo import get_mongo_db
from app.db.models import Project, Recipe


async def get_project_by_id(project_id: str) -> Project:
    mongo_db = await get_mongo_db()

    # project_data = await mongo_db["projects"].find_one({"id": project_id})
    project_data = (
        await mongo_db["projects"]
        .aggregate(
            [
                {"$match": {"id": project_id}},
                {
                    "$lookup": {
                        "from": "event_definitions",
                        "localField": "id",
                        "foreignField": "project_id",
                        "as": "settings.events",
                    }
                },
                # Filter the EventDefinitions that are not removed
                {
                    "$addFields": {
                        "settings.events": {
                            "$filter": {
                                "input": "$settings.events",
                                "as": "event",
                                "cond": {
                                    "$and": [
                                        {"$ne": ["$$event.removed", True]},
                                        {"$ne": ["$$event.event_name", None]},
                                    ]
                                },
                            }
                        }
                    }
                },
                # The lookup operation turns the events into an array of EventDefinitions
                # Convert into a Mapping {eventName: EventDefinition}
                {
                    "$addFields": {
                        "settings.events": {
                            # if the array is empty, return an empty object
                            "$cond": {
                                "if": {"$eq": [{"$size": "$settings.events"}, 0]},
                                "then": {},
                                "else": {
                                    "$arrayToObject": {
                                        "$map": {
                                            "input": "$settings.events",
                                            "as": "item",
                                            "in": {
                                                "k": "$$item.event_name",
                                                "v": "$$item",
                                            },
                                        }
                                    }
                                },
                            }
                        }
                    }
                },
            ]
        )
        .to_list(length=1)
    )

    if project_data is None or len(project_data) == 0:
        raise ValueError(f"Project {project_id} not found")

    project_data = project_data[0]

    try:
        project = Project.from_previous(project_data)
        for event_name, event in project.settings.events.items():
            if not event.recipe_id:
                recipe = Recipe(
                    org_id=project.org_id,
                    project_id=project.id,
                    recipe_type="event_detection",
                    parameters=event.model_dump(),
                )
                mongo_db["recipes"].insert_one(recipe.model_dump())
                project.settings.events[event_name].recipe_id = recipe.id

        # If the project dict is different from project_data, update the project_data
        if project.model_dump() != project_data:
            mongo_db["projects"].update_one(
                {"_id": project_data["_id"]}, {"$set": project.model_dump()}
            )
    except Exception as e:
        logger.warning(
            f"Error validating model of project {project_data.get('id', None)}: {e}"
        )
        raise ValueError(
            f"Error validating model of project {project_data.get('id', None)}"
        )

    return project
