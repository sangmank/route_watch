"""Tests for configuration module."""

import pytest
from route_watch.config import RouteConfig, NotificationConfig, Config


def test_route_config_validation():
    """Test route configuration validation."""
    # Valid configuration
    route = RouteConfig(
        name="Test Route",
        start_latlong=(37.7749, -122.4194),
        end_latlong=(37.7831, -122.4031)
    )
    assert route.name == "Test Route"
    assert route.congestion_threshold == 1.5  # default value
    
    # Invalid latitude
    with pytest.raises(ValueError, match="Latitude must be between -90 and 90"):
        RouteConfig(
            name="Invalid Route",
            start_latlong=(100, -122.4194),
            end_latlong=(37.7831, -122.4031)
        )
    
    # Invalid longitude
    with pytest.raises(ValueError, match="Longitude must be between -180 and 180"):
        RouteConfig(
            name="Invalid Route",
            start_latlong=(37.7749, -200),
            end_latlong=(37.7831, -122.4031)
        )


def test_notification_config():
    """Test notification configuration."""
    import os
    
    # Set up test environment variable
    os.environ["TELEGRAM_BOT_TOKEN"] = "test_token"
    
    try:
        config = NotificationConfig(
            tool="telegram_notifier",
            cli_args=["send", "--token", "<TELEGRAM_BOT_TOKEN>", "--message", "_NOTIFICATION_MESSAGE_"]
        )
        
        # Test message replacement
        args = config.get_command_args("Test message")
        assert "_NOTIFICATION_MESSAGE_" not in args
        assert "Test message" in args
        assert "test_token" in args
        
    finally:
        # Clean up
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)


def test_config_model():
    """Test main configuration model."""
    config = Config()
    assert config.routes == {}
    assert config.notification is None
    
    # Test route getter
    with pytest.raises(ValueError, match="Route 'nonexistent' not found"):
        config.get_route("nonexistent")