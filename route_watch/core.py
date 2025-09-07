"""Core route monitoring logic."""

import asyncio
from typing import Any, Callable, Dict, List, Optional, Tuple

from pydantic import BaseModel

from route_watch.api import create_api_client
from route_watch.config import RouteConfig


class CongestionResult(BaseModel):
    """Result of a congestion check."""
    
    route_name: str
    is_congested: bool
    current_travel_time: float  # minutes
    free_flow_travel_time: float  # minutes
    congestion_ratio: float
    alternative_available: bool = False
    alternative_travel_time: Optional[float] = None  # minutes
    timestamp: Optional[str] = None


class RouteMonitor:
    """Main class for monitoring route congestion."""
    
    def __init__(self, api_config: Dict[str, Any]):
        self.api_client = create_api_client(api_config)
    
    async def get_current_travel_time(self, route_config: RouteConfig) -> float:
        """Get current travel time with traffic for a route."""
        waypoints = route_config.free_flow_route if route_config.free_flow_route else None
        
        response = await self.api_client.get_route(
            start=route_config.start_latlong,
            end=route_config.end_latlong,
            waypoints=waypoints,
            avoid_traffic=False
        )
        
        return response.travel_time_minutes
    
    async def get_free_flow_travel_time(self, route_config: RouteConfig) -> float:
        """Get free-flow travel time without traffic for a route."""
        waypoints = route_config.free_flow_route if route_config.free_flow_route else None
        
        response = await self.api_client.get_route(
            start=route_config.start_latlong,
            end=route_config.end_latlong,
            waypoints=waypoints,
            avoid_traffic=True
        )
        
        return response.travel_time_minutes
    
    async def get_alternative_travel_time(self, route_config: RouteConfig) -> float:
        """Get travel time for an alternative route without using predefined waypoints."""
        response = await self.api_client.get_route(
            start=route_config.start_latlong,
            end=route_config.end_latlong,
            waypoints=None,  # No waypoints = alternative route
            avoid_traffic=False
        )
        
        return response.travel_time_minutes
    
    def check_route_congestion(self, route_config: RouteConfig) -> CongestionResult:
        """Check if a route is congested and if alternatives are available."""
        return asyncio.run(self._check_route_congestion_async(route_config))
    
    async def _check_route_congestion_async(self, route_config: RouteConfig) -> CongestionResult:
        """Async implementation of congestion checking."""
        from datetime import datetime
        
        # Get current and free-flow travel times concurrently
        current_time_task = self.get_current_travel_time(route_config)
        free_flow_time_task = self.get_free_flow_travel_time(route_config)
        
        current_travel_time, free_flow_travel_time = await asyncio.gather(
            current_time_task, free_flow_time_task
        )
        
        # Calculate congestion ratio
        congestion_ratio = current_travel_time / free_flow_travel_time if free_flow_travel_time > 0 else 1.0
        is_congested = congestion_ratio > route_config.congestion_threshold
        
        # Check for alternative route if congested
        alternative_available = False
        alternative_travel_time = None
        
        if is_congested:
            try:
                alternative_travel_time = await self.get_alternative_travel_time(route_config)
                # Alternative is available if it's significantly faster
                alternative_available = alternative_travel_time < (current_travel_time * 0.85)
            except Exception:
                # If alternative route check fails, assume no alternative
                alternative_available = False
                alternative_travel_time = None
        
        return CongestionResult(
            route_name=route_config.name,
            is_congested=is_congested,
            current_travel_time=current_travel_time,
            free_flow_travel_time=free_flow_travel_time,
            congestion_ratio=congestion_ratio,
            alternative_available=alternative_available,
            alternative_travel_time=alternative_travel_time,
            timestamp=datetime.now().isoformat()
        )
    
    def get_optimal_route_waypoints(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float]
    ) -> List[Tuple[float, float]]:
        """Get waypoints for the optimal route between two points."""
        return asyncio.run(self._get_optimal_route_waypoints_async(start, end))
    
    async def _get_optimal_route_waypoints_async(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float]
    ) -> List[Tuple[float, float]]:
        """Async implementation of optimal route waypoint retrieval."""
        response = await self.api_client.get_optimal_route(start, end)
        
        # Filter out start and end points, return intermediate waypoints
        waypoints = response.waypoints
        if len(waypoints) > 2:
            # Return waypoints excluding start and end
            return waypoints[1:-1]
        else:
            # No intermediate waypoints
            return []
    
    async def monitor_routes_continuously(
        self,
        route_configs: List[RouteConfig],
        check_interval: int = 300,
        callback: Optional[Callable] = None
    ) -> None:
        """Continuously monitor multiple routes."""
        while True:
            try:
                results = []
                
                # Check all routes concurrently
                tasks = [
                    self._check_route_congestion_async(route_config)
                    for route_config in route_configs
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        # Log error but continue monitoring
                        print(f"Error checking route {route_configs[i].name}: {result}")
                        continue
                    
                    # result is now guaranteed to be CongestionResult
                    assert isinstance(result, CongestionResult)
                    
                    # Call callback if provided
                    if callback and result.is_congested and result.alternative_available:
                        try:
                            callback(result)
                        except Exception as e:
                            print(f"Error in callback for route {result.route_name}: {e}")
                
                # Wait for next check
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait a minute before retrying