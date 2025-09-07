"""Command-line interface for route_watch."""

import sys
from pathlib import Path
from typing import Optional

import click
from dotenv import load_dotenv

from route_watch.config import Config
from route_watch.core import RouteMonitor
from route_watch.notifications import NotificationService


@click.group(invoke_without_command=True)
@click.option('--version', is_flag=True, help='Show version and exit')
@click.pass_context
def cli(ctx: click.Context, version: bool) -> None:
    """route_watch: CLI tool for monitoring route traffic congestion."""
    if version:
        from route_watch import __version__
        click.echo(f"route_watch {__version__}")
        return
    
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()
@click.option(
    '--config-file', '-c',
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help='Path to configuration file (TOML, YAML, or JSON)'
)
@click.option(
    '--route', '-r',
    required=True,
    help='Name of the route to check'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose output'
)
def check(config_file: Path, route: str, verbose: bool) -> None:
    """Run a one-time congestion check for a specific route."""
    load_dotenv()
    
    try:
        config = Config.load_from_file(config_file)
        route_config = config.get_route(route)
        
        # Check if using mock API and warn user
        provider = config.api_config.get("provider", "").lower()
        if verbose and (not provider or provider == "mock"):
            click.echo("⚠️  Warning: Using mock API for testing.", err=True)
            click.echo("   For real traffic data, configure 'provider = \"mapbox\"' or 'provider = \"google\"' in your config.", err=True)
        
        monitor = RouteMonitor(config.api_config)
        notification_service = NotificationService(config.notification) if config.notification else None
        
        if verbose:
            click.echo(f"Checking route: {route_config.name}")
            click.echo(f"From: {route_config.start_latlong}")
            click.echo(f"To: {route_config.end_latlong}")
        
        result = monitor.check_route_congestion(route_config)
        
        if result.is_congested:
            click.echo(f"⚠️  Route '{route_config.name}' is congested!")
            click.echo(f"Current travel time: {result.current_travel_time:.1f} minutes")
            click.echo(f"Free-flow travel time: {result.free_flow_travel_time:.1f} minutes")
            click.echo(f"Congestion ratio: {result.congestion_ratio:.2f}")
            
            if result.alternative_available:
                click.echo(f"✅ Faster alternative available: {result.alternative_travel_time:.1f} minutes")
                
                if notification_service:
                    message = (
                        f"🚦 Traffic Alert: {route_config.name} is congested! "
                        f"Current: {result.current_travel_time:.1f}min, "
                        f"Alternative: {result.alternative_travel_time:.1f}min"
                    )
                    notification_service.send_notification(message)
                    click.echo("📱 Notification sent")
            else:
                click.echo("❌ No faster alternative found")
        else:
            click.echo(f"✅ Route '{route_config.name}' is clear")
            if verbose:
                click.echo(f"Current travel time: {result.current_travel_time:.1f} minutes")
                click.echo(f"Free-flow travel time: {result.free_flow_travel_time:.1f} minutes")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command('populate-free-flow')
@click.option(
    '--config-file', '-c',
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help='Path to configuration file (TOML, YAML, or JSON)'
)
@click.option(
    '--route', '-r',
    required=True,
    help='Name of the route to populate free-flow data for'
)
@click.option(
    '--save', '-s',
    is_flag=True,
    help='Save the updated configuration back to file'
)
def populate_free_flow(config_file: Path, route: str, save: bool) -> None:
    """Populate free-flow route waypoints for a specific route."""
    load_dotenv()
    
    try:
        config = Config.load_from_file(config_file)
        route_config = config.get_route(route)
        
        # Check if using mock API and warn user
        provider = config.api_config.get("provider", "").lower()
        if not provider or provider == "mock":
            click.echo("⚠️  Warning: Using mock API for testing. This will generate fake waypoints.", err=True)
            click.echo("   For real routes, configure 'provider = \"mapbox\"' or 'provider = \"google\"' in your config.", err=True)
        
        monitor = RouteMonitor(config.api_config)
        
        click.echo(f"Fetching optimal route for: {route_config.name}")
        click.echo(f"From: {route_config.start_latlong}")
        click.echo(f"To: {route_config.end_latlong}")
        
        waypoints = monitor.get_optimal_route_waypoints(
            route_config.start_latlong,
            route_config.end_latlong
        )
        
        # Update the route configuration
        route_config.free_flow_route = waypoints
        config.routes[route] = route_config
        
        click.echo(f"✅ Found optimal route with {len(waypoints)} waypoints")
        
        if save:
            config.save_to_file(config_file)
            click.echo(f"💾 Configuration saved to {config_file}")
        else:
            click.echo("Use --save flag to save the configuration")
            click.echo(f"Free-flow waypoints: {waypoints}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    '--config-file', '-c',
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help='Path to configuration file (TOML, YAML, or JSON)'
)
@click.option(
    '--route', '-r',
    help='Specific route to watch (default: all routes)'
)
@click.option(
    '--interval', '-i',
    type=int,
    default=300,
    help='Check interval in seconds (default: 300)'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose output'
)
def watch(config_file: Path, route: Optional[str], interval: int, verbose: bool) -> None:
    """Continuously monitor routes for congestion."""
    load_dotenv()
    
    try:
        import time
        
        config = Config.load_from_file(config_file)
        monitor = RouteMonitor(config.api_config)
        notification_service = NotificationService(config.notification) if config.notification else None
        
        routes_to_watch = [route] if route else list(config.routes.keys())
        
        click.echo("🔍 Starting route monitoring...")
        click.echo(f"Routes: {', '.join(routes_to_watch)}")
        click.echo(f"Check interval: {interval} seconds")
        click.echo("Press Ctrl+C to stop")
        
        while True:
            try:
                for route_name in routes_to_watch:
                    route_config = config.get_route(route_name)
                    
                    if verbose:
                        click.echo(f"Checking {route_config.name}...")
                    
                    result = monitor.check_route_congestion(route_config)
                    
                    if result.is_congested and result.alternative_available:
                        message = (
                            f"🚦 Traffic Alert: {route_config.name} is congested! "
                            f"Current: {result.current_travel_time:.1f}min, "
                            f"Alternative: {result.alternative_travel_time:.1f}min"
                        )
                        
                        click.echo(f"⚠️  {message}")
                        
                        if notification_service:
                            notification_service.send_notification(message)
                            click.echo("📱 Notification sent")
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                click.echo("\n👋 Stopping route monitoring...")
                break
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
def version() -> None:
    """Show version information."""
    from route_watch import __version__
    click.echo(f"route_watch {__version__}")


if __name__ == '__main__':
    cli()