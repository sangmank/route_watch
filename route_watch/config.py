"""Configuration models and loading for route_watch."""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import toml
import yaml
from pydantic import BaseModel, Field, field_validator


class RouteConfig(BaseModel):
    """Configuration for a single route to monitor."""
    
    name: str = Field(..., description="Human-readable name for the route")
    start_latlong: Tuple[float, float] = Field(..., description="Starting coordinates [lat, lng]")
    end_latlong: Tuple[float, float] = Field(..., description="Ending coordinates [lat, lng]")
    free_flow_route: List[Tuple[float, float]] = Field(
        default_factory=list, 
        description="Waypoints for the optimal free-flow route"
    )
    congestion_threshold: float = Field(
        default=1.5, 
        description="Travel time ratio threshold for congestion detection"
    )

    @field_validator('start_latlong', 'end_latlong')
    @classmethod
    def validate_coordinates(cls, v: Tuple[float, float]) -> Tuple[float, float]:
        """Validate latitude/longitude coordinates."""
        if len(v) != 2:
            raise ValueError("Coordinates must be a tuple of (lat, lng)")
        lat, lng = v
        if not (-90 <= lat <= 90):
            raise ValueError(f"Latitude must be between -90 and 90, got {lat}")
        if not (-180 <= lng <= 180):
            raise ValueError(f"Longitude must be between -180 and 180, got {lng}")
        return v

    @field_validator('free_flow_route')
    @classmethod
    def validate_waypoints(cls, v: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Validate waypoint coordinates."""
        for waypoint in v:
            if len(waypoint) != 2:
                raise ValueError("Each waypoint must be a tuple of (lat, lng)")
            lat, lng = waypoint
            if not (-90 <= lat <= 90):
                raise ValueError(f"Latitude must be between -90 and 90, got {lat}")
            if not (-180 <= lng <= 180):
                raise ValueError(f"Longitude must be between -180 and 180, got {lng}")
        return v


class NotificationConfig(BaseModel):
    """Configuration for notification system."""
    
    tool: str = Field(..., description="CLI tool to use for notifications")
    cli_args: List[str] = Field(..., description="Arguments to pass to the CLI tool")

    def get_command_args(self, message: str) -> List[str]:
        """Replace message placeholder and expand environment variables."""
        expanded_args = []
        for arg in self.cli_args:
            if arg == "_NOTIFICATION_MESSAGE_":
                expanded_args.append(message)
            elif arg.startswith("<") and arg.endswith(">"):
                env_var = arg[1:-1]
                env_value = os.getenv(env_var)
                if env_value is None:
                    raise ValueError(f"Environment variable {env_var} is not set")
                expanded_args.append(env_value)
            else:
                expanded_args.append(arg)
        return expanded_args


class Config(BaseModel):
    """Main configuration for route_watch."""
    
    routes: Dict[str, RouteConfig] = Field(default_factory=dict, description="Route configurations")
    notification: Optional[NotificationConfig] = Field(None, description="Notification configuration")
    api_config: Dict[str, Any] = Field(
        default_factory=dict, 
        description="API-specific configuration"
    )

    @classmethod
    def load_from_file(cls, file_path: Union[str, Path]) -> "Config":
        """Load configuration from a TOML, YAML, or JSON file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        
        content = path.read_text()
        
        # Determine file format and parse
        if path.suffix.lower() in ['.toml']:
            data = toml.loads(content)
        elif path.suffix.lower() in ['.yml', '.yaml']:
            data = yaml.safe_load(content)
        elif path.suffix.lower() in ['.json']:
            data = json.loads(content)
        else:
            # Try to auto-detect format
            try:
                data = toml.loads(content)
            except toml.TomlDecodeError:
                try:
                    data = yaml.safe_load(content)
                except yaml.YAMLError:
                    try:
                        data = json.loads(content)
                    except json.JSONDecodeError:
                        raise ValueError(f"Unable to parse configuration file: {path}")
        
        # Convert route.* format to routes dict
        routes = {}
        notification = None
        api_config = {}
        
        for key, value in data.items():
            if key.startswith("route."):
                route_name = key[6:]  # Remove "route." prefix
                routes[route_name] = RouteConfig(**value)
            elif key == "route":
                # Handle nested route structure from TOML
                for route_name, route_data in value.items():
                    routes[route_name] = RouteConfig(**route_data)
            elif key == "notification":
                notification = NotificationConfig(**value)
            elif key == "api_config":
                api_config = value
            else:
                # Handle other top-level config items (like provider, api_key)
                api_config[key] = value
        
        return cls(routes=routes, notification=notification, api_config=api_config)

    def get_route(self, route_name: str) -> RouteConfig:
        """Get a specific route configuration by name."""
        if route_name not in self.routes:
            raise ValueError(f"Route '{route_name}' not found in configuration")
        return self.routes[route_name]

    def save_to_file(self, file_path: Union[str, Path]) -> None:
        """Save configuration to a file."""
        path = Path(file_path)
        
        # Convert back to route.* format for saving
        data = {}
        
        for route_name, route_config in self.routes.items():
            data[f"route.{route_name}"] = route_config.model_dump()
        
        if self.notification:
            data["notification"] = self.notification.model_dump()
        
        if self.api_config:
            data.update(self.api_config)
        
        # Save based on file extension
        if path.suffix.lower() in ['.toml']:
            content = toml.dumps(data)
        elif path.suffix.lower() in ['.yml', '.yaml']:
            content = yaml.dump(data, default_flow_style=False)
        elif path.suffix.lower() in ['.json']:
            content = json.dumps(data, indent=2)
        else:
            # Default to TOML
            content = toml.dumps(data)
        
        path.write_text(content)