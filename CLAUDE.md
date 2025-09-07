# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

route_watch is a Python CLI tool that monitors specific routes for traffic congestion and sends notifications when congestion is detected and faster alternatives are available. The tool is designed to be API-agnostic and uses external notification services.

## Development Setup

This project uses Poetry for dependency management. Key commands:

```bash
# Install dependencies
poetry install

# Run the CLI tool
poetry run route_watch --help

# Run a one-time check
poetry run route_watch check --config-file "routes.toml" --route "Morning Commute"

# Populate free-flow route data
poetry run route_watch populate-free-flow --config-file "routes.toml" --route "Morning Commute"
```

## Testing and Code Quality

```bash
# Run tests
poetry run pytest

# Run type checking
poetry run mypy route_watch/

# Run linting
poetry run ruff check route_watch/

# Format code
poetry run ruff format route_watch/
```

## Architecture

The codebase follows a modular design with clear separation of concerns:

- **CLI Layer**: Argument parsing and command handling (using Click or argparse)
- **Core Logic**: Route monitoring, congestion detection, and API interaction
- **Configuration**: Pydantic models for validating TOML/YAML/JSON config files
- **API Abstraction**: Plugin-style architecture for different traffic APIs (Mapbox, Google Maps, TomTom)
- **Notification**: External CLI command execution for notifications

## Configuration

The tool supports multiple configuration formats (TOML, YAML, JSON) with the following structure:

- `route.*`: Route definitions with start/end coordinates and free-flow waypoints
- `notification`: External notification tool configuration with CLI arguments
- Environment variables: Used for sensitive data like API tokens (e.g., `<TELEGRAM_BOT_TOKEN>`)

## Key Design Principles

- **API Agnostic**: Core logic is separated from specific traffic APIs
- **Extensible Notifications**: Uses external CLI commands for notifications
- **Configurable Thresholds**: Congestion detection based on travel time ratios
- **Type Safety**: Full type hints throughout the codebase
- **Modular**: Clear separation between CLI, core logic, and external integrations

## Code Standards

- Follow PEP 8 for Python style
- Use type hints for all functions and classes
- Write docstrings for public APIs
- Use Pydantic for configuration validation
- Separate CLI logic from core functionality