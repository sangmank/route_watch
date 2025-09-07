"""Notification system for route_watch."""

import subprocess
from typing import Optional

from route_watch.config import NotificationConfig


class NotificationService:
    """Service for sending notifications via external CLI tools."""
    
    def __init__(self, config: Optional[NotificationConfig] = None):
        self.config = config
    
    def send_notification(self, message: str) -> bool:
        """Send a notification using the configured CLI tool.
        
        Args:
            message: The message to send
            
        Returns:
            True if notification was sent successfully, False otherwise
        """
        if not self.config:
            print(f"No notification config - would send: {message}")
            return False
        
        try:
            # Get command arguments with message substitution
            command_args = [self.config.tool] + self.config.get_command_args(message)
            
            # Execute the command
            result = subprocess.run(
                command_args,
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout
            )
            
            if result.returncode == 0:
                return True
            else:
                print(f"Notification command failed with code {result.returncode}")
                print(f"stderr: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("Notification command timed out")
            return False
        except FileNotFoundError:
            print(f"Notification tool '{self.config.tool}' not found")
            return False
        except Exception as e:
            print(f"Error sending notification: {e}")
            return False
    
    def test_notification(self) -> bool:
        """Test the notification system with a sample message.
        
        Returns:
            True if test notification was sent successfully, False otherwise
        """
        test_message = "🧪 route_watch notification test"
        print(f"Sending test notification: {test_message}")
        return self.send_notification(test_message)


class ConsoleNotificationService(NotificationService):
    """Simple console-based notification service for testing."""
    
    def __init__(self):
        super().__init__(None)
    
    def send_notification(self, message: str) -> bool:
        """Print notification to console."""
        print(f"📱 NOTIFICATION: {message}")
        return True


# Convenience functions for common notification services

def create_telegram_notifier_config(bot_token_env: str, chat_id_env: str) -> NotificationConfig:
    """Create a NotificationConfig for telegram_notifier CLI tool.
    
    Args:
        bot_token_env: Environment variable name for bot token (e.g., "TELEGRAM_BOT_TOKEN")
        chat_id_env: Environment variable name for chat ID (e.g., "TELEGRAM_CHAT_ID")
    """
    return NotificationConfig(
        tool="telegram_notifier",
        cli_args=[
            "send",
            "--token", f"<{bot_token_env}>",
            "--chat-id", f"<{chat_id_env}>",
            "--message", "_NOTIFICATION_MESSAGE_"
        ]
    )


def create_slack_cli_config(webhook_env: str) -> NotificationConfig:
    """Create a NotificationConfig for slack CLI tool.
    
    Args:
        webhook_env: Environment variable name for Slack webhook URL
    """
    return NotificationConfig(
        tool="slack",
        cli_args=[
            "chat", "send",
            "--webhook-url", f"<{webhook_env}>",
            "--text", "_NOTIFICATION_MESSAGE_"
        ]
    )


def create_mail_config(recipient: str, subject: str = "Traffic Alert") -> NotificationConfig:
    """Create a NotificationConfig for system mail command.
    
    Args:
        recipient: Email address to send to
        subject: Email subject line
    """
    return NotificationConfig(
        tool="mail",
        cli_args=[
            "-s", subject,
            recipient
        ]
    )


def create_ntfy_config(topic: str, server: str = "ntfy.sh") -> NotificationConfig:
    """Create a NotificationConfig for ntfy.sh push notifications.
    
    Args:
        topic: ntfy topic name
        server: ntfy server URL (default: ntfy.sh)
    """
    return NotificationConfig(
        tool="curl",
        cli_args=[
            "-d", "_NOTIFICATION_MESSAGE_",
            f"https://{server}/{topic}"
        ]
    )