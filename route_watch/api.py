"""API abstraction layer for traffic services."""

import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

import httpx
from pydantic import BaseModel


class RouteResponse(BaseModel):
    """Response from a route API call."""
    
    travel_time_minutes: float
    distance_km: float
    waypoints: List[Tuple[float, float]]
    route_geometry: Optional[str] = None


class TrafficAPI(ABC):
    """Abstract base class for traffic API providers."""
    
    @abstractmethod
    async def get_route(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        waypoints: Optional[List[Tuple[float, float]]] = None,
        avoid_traffic: bool = False
    ) -> RouteResponse:
        """Get route information between two points."""
        pass

    @abstractmethod
    async def get_optimal_route(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float]
    ) -> RouteResponse:
        """Get the optimal route without traffic considerations."""
        pass


class MapboxAPI(TrafficAPI):
    """Mapbox Directions API implementation."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.mapbox.com/directions/v5/mapbox"
    
    async def get_route(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        waypoints: Optional[List[Tuple[float, float]]] = None,
        avoid_traffic: bool = False
    ) -> RouteResponse:
        """Get route from Mapbox Directions API."""
        profile = "driving-traffic" if not avoid_traffic else "driving"
        
        # Format coordinates as lng,lat for Mapbox
        coords = [f"{start[1]},{start[0]}"]
        if waypoints:
            coords.extend([f"{wp[1]},{wp[0]}" for wp in waypoints])
        coords.append(f"{end[1]},{end[0]}")
        
        coordinates = ";".join(coords)
        url = f"{self.base_url}/{profile}/{coordinates}"
        
        params = {
            "access_token": self.api_key,
            "geometries": "geojson",
            "overview": "full",
            "steps": "false"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        
        if not data.get("routes"):
            raise ValueError("No routes found")
        
        route = data["routes"][0]
        duration_seconds = route["duration"]
        distance_meters = route["distance"]
        
        # Extract waypoints from geometry
        geometry = route["geometry"]["coordinates"]
        route_waypoints = [(lat, lng) for lng, lat in geometry]
        
        return RouteResponse(
            travel_time_minutes=duration_seconds / 60,
            distance_km=distance_meters / 1000,
            waypoints=route_waypoints,
            route_geometry=str(route["geometry"])
        )
    
    async def get_optimal_route(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float]
    ) -> RouteResponse:
        """Get optimal route without traffic considerations."""
        return await self.get_route(start, end, avoid_traffic=True)


class GoogleMapsAPI(TrafficAPI):
    """Google Maps Directions API implementation."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://maps.googleapis.com/maps/api/directions"
    
    async def get_route(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        waypoints: Optional[List[Tuple[float, float]]] = None,
        avoid_traffic: bool = False
    ) -> RouteResponse:
        """Get route from Google Maps Directions API."""
        params = {
            "origin": f"{start[0]},{start[1]}",
            "destination": f"{end[0]},{end[1]}",
            "key": self.api_key,
            "units": "metric"
        }
        
        if waypoints:
            waypoint_str = "|".join([f"{wp[0]},{wp[1]}" for wp in waypoints])
            params["waypoints"] = waypoint_str
        
        if not avoid_traffic:
            params["departure_time"] = "now"
        
        url = f"{self.base_url}/json"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        
        if data["status"] != "OK" or not data.get("routes"):
            raise ValueError(f"Google Maps API error: {data.get('status', 'No routes found')}")
        
        route = data["routes"][0]
        leg = route["legs"][0]
        
        # Use duration_in_traffic if available, otherwise use duration
        if not avoid_traffic and "duration_in_traffic" in leg:
            duration_seconds = leg["duration_in_traffic"]["value"]
        else:
            duration_seconds = leg["duration"]["value"]
        
        distance_meters = leg["distance"]["value"]
        
        # Extract waypoints from overview_polyline
        # This is a simplified extraction - in practice, you'd decode the polyline
        route_waypoints = [start, end]
        
        return RouteResponse(
            travel_time_minutes=duration_seconds / 60,
            distance_km=distance_meters / 1000,
            waypoints=route_waypoints
        )
    
    async def get_optimal_route(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float]
    ) -> RouteResponse:
        """Get optimal route without traffic considerations."""
        return await self.get_route(start, end, avoid_traffic=True)


class MockAPI(TrafficAPI):
    """Mock API for testing purposes."""
    
    def __init__(self, **kwargs):
        self.base_travel_time = 30  # minutes
        self.traffic_multiplier = 1.5
    
    async def get_route(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        waypoints: Optional[List[Tuple[float, float]]] = None,
        avoid_traffic: bool = False
    ) -> RouteResponse:
        """Get mock route data."""
        # Calculate simple distance-based travel time
        import math
        
        lat_diff = end[0] - start[0]
        lng_diff = end[1] - start[1]
        distance_km = math.sqrt(lat_diff**2 + lng_diff**2) * 111  # Rough km conversion
        
        base_time = max(self.base_travel_time, distance_km * 2)  # 2 min per km base
        
        if avoid_traffic:
            travel_time = base_time
        else:
            travel_time = base_time * self.traffic_multiplier
        
        route_waypoints = [start]
        if waypoints:
            route_waypoints.extend(waypoints)
        else:
            # For optimal route requests, generate some fake intermediate waypoints
            # This is useful for testing the populate-free-flow functionality
            if avoid_traffic and distance_km > 1:  # Generate waypoints for routes > 1km
                # Generate 1-3 intermediate waypoints based on distance
                num_points = min(3, max(1, int(distance_km / 2)))
                for i in range(1, num_points + 1):
                    ratio = i / (num_points + 1)
                    intermediate_lat = start[0] + ratio * (end[0] - start[0])
                    intermediate_lng = start[1] + ratio * (end[1] - start[1])
                    # Add small random offset to simulate real route
                    import random
                    intermediate_lat += random.uniform(-0.001, 0.001)
                    intermediate_lng += random.uniform(-0.001, 0.001)
                    route_waypoints.append((intermediate_lat, intermediate_lng))
        
        route_waypoints.append(end)
        
        return RouteResponse(
            travel_time_minutes=travel_time,
            distance_km=distance_km,
            waypoints=route_waypoints
        )
    
    async def get_optimal_route(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float]
    ) -> RouteResponse:
        """Get optimal mock route without traffic."""
        return await self.get_route(start, end, avoid_traffic=True)


def create_api_client(api_config: Dict[str, Any]) -> TrafficAPI:
    """Factory function to create the appropriate API client."""
    provider = api_config.get("provider")
    
    # Warn if no provider is configured
    if not provider:
        import sys
        print("Warning: No API provider configured. Using mock API for testing.", file=sys.stderr)
        print("Add 'provider = \"mapbox\"' or 'provider = \"google\"' to your config file.", file=sys.stderr)
        provider = "mock"
    
    provider = provider.lower()
    
    if provider == "mapbox":
        api_key = api_config.get("api_key") or os.getenv("MAPBOX_API_KEY")
        if not api_key:
            raise ValueError("Mapbox API key not found in config or MAPBOX_API_KEY environment variable")
        return MapboxAPI(api_key)
    
    elif provider == "google":
        api_key = api_config.get("api_key") or os.getenv("GOOGLE_MAPS_API_KEY")
        if not api_key:
            raise ValueError("Google Maps API key not found in config or GOOGLE_MAPS_API_KEY environment variable")
        return GoogleMapsAPI(api_key)
    
    elif provider == "mock":
        return MockAPI(**api_config)
    
    else:
        raise ValueError(f"Unsupported API provider: {provider}")