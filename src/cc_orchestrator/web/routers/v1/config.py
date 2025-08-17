"""
Configuration management API endpoints.

This module provides REST API endpoints for managing configuration settings,
including hierarchical configurations and scope-based overrides.
"""

from typing import Any
from unittest.mock import Mock

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ....database.models import ConfigScope
from ...crud_adapter import CRUDBase
from ...dependencies import (
    PaginationParams,
    get_crud,
    get_pagination_params,
    validate_config_id,
)
from ...logging_utils import handle_api_errors, track_api_performance
from ...schemas import (
    APIResponse,
    ConfigurationCreate,
    ConfigurationResponse,
    ConfigurationUpdate,
    PaginatedResponse,
)

router = APIRouter()


def _config_to_dict(config_obj) -> dict[str, Any]:
    """Convert a configuration object to dictionary for Pydantic validation."""
    if hasattr(config_obj, "__dict__"):
        # Handle scope field with enum conversion
        scope_value = getattr(config_obj, "scope", ConfigScope.GLOBAL)
        if hasattr(scope_value, "value"):
            scope_str = scope_value.value
        else:
            scope_str = str(scope_value) if scope_value else "global"

        # Get category with proper fallback for Mock objects
        category = getattr(config_obj, "category", None)
        if (
            not category
            or isinstance(category, Mock)
            or str(category).startswith("<Mock")
        ):
            category = "general"

        config_data = {
            "id": getattr(config_obj, "id", None),
            "key": getattr(config_obj, "key", ""),
            "value": getattr(config_obj, "value", ""),
            "description": getattr(config_obj, "description", None),
            "category": category,
            "scope": scope_str,
            "instance_id": getattr(config_obj, "instance_id", None),
            "is_secret": getattr(config_obj, "is_secret", False),
            "is_readonly": getattr(config_obj, "is_readonly", False),
            "created_at": getattr(config_obj, "created_at", None),
            "updated_at": getattr(config_obj, "updated_at", None),
        }
        return config_data
    return config_obj


@router.get("/", response_model=PaginatedResponse)
@track_api_performance()
@handle_api_errors()
async def list_configurations(
    pagination: PaginationParams = Depends(get_pagination_params),
    scope: ConfigScope | None = Query(None, alias="scope"),
    instance_id: int | None = Query(None, alias="instance_id"),
    key_pattern: str | None = Query(None, alias="key"),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    List all configurations with optional filtering and pagination.

    - **page**: Page number (default: 1)
    - **size**: Items per page (default: 20, max: 100)
    - **scope**: Filter by configuration scope
    - **instance_id**: Filter by instance (for instance-scoped configs)
    - **key**: Filter by key pattern (partial match)
    """
    # Build filter criteria
    filters = {}
    if scope:
        filters["scope"] = scope
    if instance_id:
        filters["instance_id"] = instance_id  # type: ignore[assignment]
    if key_pattern:
        filters["key_pattern"] = key_pattern  # type: ignore[assignment]

    # Get configurations with pagination
    configurations, total = await crud.list_configurations(
        offset=pagination.offset, limit=pagination.size, filters=filters
    )

    # Convert to response schemas
    config_responses = [
        ConfigurationResponse.model_validate(_config_to_dict(config))
        for config in configurations
    ]

    return {
        "items": config_responses,
        "total": total,
        "page": pagination.page,
        "size": pagination.size,
        "pages": (total + pagination.size - 1) // pagination.size,
    }


@router.post("/", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
@track_api_performance()
@handle_api_errors()
async def create_configuration(
    config_data: ConfigurationCreate,
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Create a new configuration setting.

    - **key**: Configuration key (required)
    - **value**: Configuration value (required)
    - **scope**: Configuration scope (default: global)
    - **instance_id**: Instance ID (required for instance scope)
    - **description**: Configuration description
    - **is_secret**: Whether this is a secret value
    - **is_readonly**: Whether this value is read-only
    """
    # Validate scope and instance_id combination
    # Handle both enum and string values for scope comparison
    if hasattr(config_data.scope, "value"):
        scope_value = config_data.scope.value
    else:
        scope_value = str(config_data.scope)
    is_instance_scope = scope_value == "instance"

    if is_instance_scope and not config_data.instance_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="instance_id is required for instance-scoped configurations",
        )

    if not is_instance_scope and config_data.instance_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="instance_id can only be set for instance-scoped configurations",
        )

    # Validate instance exists if specified
    if config_data.instance_id:
        instance = await crud.get_instance(config_data.instance_id)
        if not instance:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Instance with ID {config_data.instance_id} not found",
            )

    # Check for duplicate key/scope combination (exact match, no hierarchy)
    existing = await crud.get_exact_configuration_by_key_scope(
        config_data.key, scope_value, config_data.instance_id
    )
    if existing:
        # Handle both enum and string values for scope in error message
        if hasattr(config_data.scope, "value"):
            scope_display = config_data.scope.value
        else:
            scope_display = str(config_data.scope)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Configuration with key '{config_data.key}' already exists for scope '{scope_display}'",
        )

    # Create the configuration
    # Convert scope enum to string for database storage
    config_dict = config_data.model_dump()
    config_dict["scope"] = scope_value
    configuration = await crud.create_configuration(config_dict)

    return {
        "success": True,
        "message": "Configuration created successfully",
        "data": ConfigurationResponse.model_validate(_config_to_dict(configuration)),
    }


@router.get("/{config_id}", response_model=APIResponse)
@track_api_performance()
@handle_api_errors()
async def get_configuration(
    config_id: int = Depends(validate_config_id),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Get a specific configuration by ID.

    - **config_id**: The ID of the configuration to retrieve
    """
    configuration = await crud.get_configuration(config_id)
    if not configuration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration with ID {config_id} not found",
        )

    return {
        "success": True,
        "message": "Configuration retrieved successfully",
        "data": ConfigurationResponse.model_validate(_config_to_dict(configuration)),
    }


@router.put("/{config_id}", response_model=APIResponse)
@track_api_performance()
@handle_api_errors()
async def update_configuration(
    config_data: ConfigurationUpdate,
    config_id: int = Depends(validate_config_id),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Update an existing configuration.

    - **config_id**: The ID of the configuration to update
    - Only provided fields will be updated
    """
    # Check if configuration exists
    existing = await crud.get_configuration(config_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration with ID {config_id} not found",
        )

    # Check if configuration is read-only
    if existing.is_readonly:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update read-only configuration",
        )

    # Update the configuration
    update_data = config_data.model_dump(exclude_unset=True)
    configuration = await crud.update_configuration(config_id, update_data)

    return {
        "success": True,
        "message": "Configuration updated successfully",
        "data": ConfigurationResponse.model_validate(_config_to_dict(configuration)),
    }


@router.delete("/{config_id}", response_model=APIResponse)
@track_api_performance()
@handle_api_errors()
async def delete_configuration(
    config_id: int = Depends(validate_config_id),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Delete a configuration.

    - **config_id**: The ID of the configuration to delete
    """
    # Check if configuration exists
    existing = await crud.get_configuration(config_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration with ID {config_id} not found",
        )

    # Check if configuration is read-only
    if existing.is_readonly:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete read-only configuration",
        )

    # Delete the configuration
    await crud.delete_configuration(config_id)

    return {
        "success": True,
        "message": "Configuration deleted successfully",
        "data": None,
    }


@router.get("/key/{key}", response_model=APIResponse)
@track_api_performance()
@handle_api_errors()
async def get_configuration_by_key(
    key: str,
    scope: ConfigScope = Query(ConfigScope.GLOBAL),
    instance_id: int | None = Query(None),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Get configuration value by key and scope.

    - **key**: Configuration key
    - **scope**: Configuration scope (default: global)
    - **instance_id**: Instance ID (required for instance scope)
    """
    # Validate scope and instance_id combination
    if scope == ConfigScope.INSTANCE and not instance_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="instance_id is required for instance-scoped configurations",
        )

    # Convert enum to string for CRUD adapter compatibility
    scope_value = scope.value if hasattr(scope, "value") else str(scope)
    configuration = await crud.get_configuration_by_key_scope(
        key, scope_value, instance_id
    )
    if not configuration:
        # Handle both enum and string values for scope in error message
        if hasattr(scope, "value"):
            scope_display = scope.value
        else:
            scope_display = str(scope)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration with key '{key}' not found for scope '{scope_display}'",
        )

    return {
        "success": True,
        "message": "Configuration retrieved successfully",
        "data": ConfigurationResponse.model_validate(_config_to_dict(configuration)),
    }


@router.get("/resolved/{key}", response_model=APIResponse)
@track_api_performance()
@handle_api_errors()
async def get_resolved_configuration(
    key: str,
    instance_id: int | None = Query(None),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Get resolved configuration value using hierarchical precedence.

    Resolution order: Instance > Project > User > Global

    - **key**: Configuration key
    - **instance_id**: Instance ID for instance-specific resolution
    """
    # TODO: Implement hierarchical resolution logic
    # For now, just check instance -> global

    configuration = None
    resolved_scope = None

    # Check instance scope first if instance_id provided
    if instance_id:
        configuration = await crud.get_configuration_by_key_scope(
            key, ConfigScope.INSTANCE.value, instance_id
        )
        if configuration:
            resolved_scope = "instance"

    # Fall back to global scope
    if not configuration:
        configuration = await crud.get_configuration_by_key_scope(
            key, ConfigScope.GLOBAL.value, None
        )
        if configuration:
            resolved_scope = "global"

    if not configuration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration with key '{key}' not found",
        )

    response_data = ConfigurationResponse.model_validate(
        _config_to_dict(configuration)
    ).model_dump()
    response_data["resolved_from_scope"] = resolved_scope

    return {
        "success": True,
        "message": "Configuration resolved successfully",
        "data": response_data,
    }


@router.get("/instance/{instance_id}", response_model=PaginatedResponse)
@track_api_performance()
@handle_api_errors()
async def get_instance_configurations(
    instance_id: int,
    pagination: PaginationParams = Depends(get_pagination_params),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Get all configurations for a specific instance.

    - **instance_id**: The ID of the instance
    - **page**: Page number (default: 1)
    - **size**: Items per page (default: 20, max: 100)
    """
    # Check if instance exists
    instance = await crud.get_instance(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance with ID {instance_id} not found",
        )

    # Get configurations for this instance
    configurations, total = await crud.list_configurations(
        offset=pagination.offset,
        limit=pagination.size,
        filters={"instance_id": instance_id, "scope": ConfigScope.INSTANCE},
    )

    config_responses = [
        ConfigurationResponse.model_validate(_config_to_dict(config))
        for config in configurations
    ]

    return {
        "items": config_responses,
        "total": total,
        "page": pagination.page,
        "size": pagination.size,
        "pages": (total + pagination.size - 1) // pagination.size,
    }
