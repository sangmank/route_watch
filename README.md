# route_watch

A CLI tool for monitoring route traffic congestion and sending notifications when faster alternatives are available.

## Features

- 🚗 **Route Monitoring**: Check specific routes for traffic congestion
- 📱 **Smart Notifications**: Get alerts only when congestion is detected AND faster alternatives exist  
- 🔌 **API Agnostic**: Support for Mapbox, Google Maps, or mock data for testing
- ⚙️ **Flexible Configuration**: TOML, YAML, or JSON configuration files
- 🔔 **Extensible Notifications**: Works with any CLI notification tool (Telegram, Slack, etc.)
- 🔄 **Continuous Monitoring**: Watch routes continuously with configurable intervals

## Installation

### From Source

```bash
git clone https://github.com/USERNAME/route_watch.git
cd route_watch
poetry install
```

### System-wide Installation

```bash
poetry build
pip install dist/route_watch-*.whl
```

## Quick Start

1. **Copy the example configuration:**
   ```bash
   cp example_routes.toml my_routes.toml
   ```

2. **Edit your configuration** to add your routes and API provider:
   ```toml
   # Set API provider (mapbox, google, or mock)
   provider = "mapbox"
   # api_key = "your_api_key_here"  # or set MAPBOX_API_KEY env var
   
   [route.morning_commute]
   name = "Morning Commute"
   start_latlong = [37.7749, -122.4194]  # Your start coordinates
   end_latlong = [37.7831, -122.4031]    # Your destination
   congestion_threshold = 1.5            # 50% slower = congested
   ```

3. **Test your configuration:**
   ```bash
   route_watch check --config-file my_routes.toml --route morning_commute --verbose
   ```

## Usage

### One-time Route Check
```bash
route_watch check --config-file routes.toml --route morning_commute --verbose
```

### Populate Free-flow Route Data
```bash
route_watch populate-free-flow --config-file routes.toml --route morning_commute --save
```

### Continuous Monitoring
```bash
# Monitor all routes every 5 minutes
route_watch watch --config-file routes.toml --interval 300

# Monitor specific route
route_watch watch --config-file routes.toml --route morning_commute --interval 180
```

## Configuration

### Route Configuration

```toml
[route.route_name]
name = "Human readable name"
start_latlong = [latitude, longitude]     # Start coordinates
end_latlong = [latitude, longitude]       # End coordinates  
free_flow_route = [                       # Optional: predefined waypoints
    [waypoint1_lat, waypoint1_lng],
    [waypoint2_lat, waypoint2_lng]
]
congestion_threshold = 1.5                # Traffic ratio threshold (1.5 = 50% slower)
```

### API Providers

#### Mapbox (Recommended)
```toml
provider = "mapbox"
api_key = "your_mapbox_token"  # or set MAPBOX_API_KEY env var
```

#### Google Maps
```toml  
provider = "google"
api_key = "your_google_api_key"  # or set GOOGLE_MAPS_API_KEY env var
```

#### Mock (Testing)
```toml
provider = "mock"  # No API key required
```

### Notifications

```toml
[notification]
tool = "telegram_notifier"
cli_args = [
    "send",
    "--token", "<TELEGRAM_BOT_TOKEN>",      # Environment variable
    "--chat-id", "<TELEGRAM_CHAT_ID>",      # Environment variable  
    "--message", "_NOTIFICATION_MESSAGE_"    # Placeholder for message
]
```

**Supported notification patterns:**
- `<ENV_VAR>` - Replaced with environment variable value
- `_NOTIFICATION_MESSAGE_` - Replaced with the actual alert message

## Environment Variables

- `MAPBOX_API_KEY` - Your Mapbox access token
- `GOOGLE_MAPS_API_KEY` - Your Google Maps API key  
- `TELEGRAM_BOT_TOKEN` - Your Telegram bot token
- `TELEGRAM_CHAT_ID` - Your Telegram chat ID

## Development

```bash
# Install dependencies
poetry install

# Run tests
poetry run pytest

# Type checking  
poetry run mypy route_watch/

# Linting
poetry run ruff check route_watch/

# Format code
poetry run ruff format route_watch/
```

## How It Works

1. **Congestion Detection**: Compares current travel time (with traffic) to free-flow travel time
2. **Threshold Check**: Route is "congested" when travel time ratio exceeds the configured threshold
3. **Alternative Check**: When congested, checks if alternative routes are significantly faster
4. **Smart Notifications**: Only sends alerts when BOTH congestion is detected AND alternatives exist

## Example Workflow

```
Current route: 45 minutes
Free-flow time: 30 minutes  
Ratio: 1.5 (50% slower)
Threshold: 1.5
→ Route is CONGESTED ⚠️

Alternative route: 35 minutes
Improvement: 10 minutes (22% faster)
→ Send notification 📱
```

## License

MIT License - see LICENSE file for details.

## Contributing

Pull requests welcome! Please run tests and linting before submitting:

```bash
poetry run pytest
poetry run mypy route_watch/
poetry run ruff check route_watch/
```