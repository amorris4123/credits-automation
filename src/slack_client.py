"""
Slack Client
Handles Slack API interactions for monitoring messages and posting replies
"""

import re
import logging
from typing import List, Optional, Dict
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from .config import Config

logger = logging.getLogger(__name__)


class SlackClient:
    """Client for interacting with Slack API"""

    def __init__(self, token: str = None):
        """
        Initialize Slack client

        Args:
            token: Slack bot token (defaults to Config)
        """
        self.token = token or Config.SLACK_BOT_TOKEN
        self.client = WebClient(token=self.token)
        self.bot_user_id = None

    def test_connection(self) -> bool:
        """
        Test Slack API connection and get bot user ID

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            response = self.client.auth_test()
            self.bot_user_id = response['user_id']
            logger.info(f"Successfully connected to Slack as {response['user']}")
            return True

        except SlackApiError as e:
            logger.error(f"Slack connection failed: {e}")
            return False

    def get_channel_id(self, channel_name: str) -> Optional[str]:
        """
        Get channel ID from channel name

        Args:
            channel_name: Channel name (with or without #)

        Returns:
            Channel ID if found, None otherwise
        """
        # Remove # if present
        channel_name = channel_name.lstrip('#')

        try:
            response = self.client.conversations_list(types='public_channel,private_channel')
            channels = response['channels']

            for channel in channels:
                if channel['name'] == channel_name:
                    return channel['id']

            logger.warning(f"Channel '{channel_name}' not found")
            return None

        except SlackApiError as e:
            logger.error(f"Error fetching channel list: {e}")
            return None

    def get_recent_messages(self, channel_id: str, limit: int = 100) -> List[Dict]:
        """
        Get recent messages from a channel

        Args:
            channel_id: Channel ID
            limit: Maximum number of messages to retrieve

        Returns:
            List of message dictionaries
        """
        try:
            response = self.client.conversations_history(
                channel=channel_id,
                limit=limit
            )

            messages = response['messages']
            logger.info(f"Retrieved {len(messages)} messages from channel")
            return messages

        except SlackApiError as e:
            logger.error(f"Error fetching messages: {e}")
            return []

    def extract_looker_urls(self, message_text: str) -> List[str]:
        """
        Extract Looker URLs from message text

        Args:
            message_text: Slack message text

        Returns:
            List of Looker URLs found in message

        Notes:
            - Slack formats links as <url|text> in the API
            - We extract URLs that contain looker domain
            - Filters out non-Looker links (Zendesk, etc.)
        """
        looker_urls = []

        # Slack link format: <https://url.com|display text>
        # We need to extract the URL part before the |
        link_pattern = r'<(https?://[^|>]+)(?:\|[^>]+)?>'
        matches = re.findall(link_pattern, message_text)

        for url in matches:
            # Check if it's a Looker URL
            if 'looker.com' in url.lower():
                looker_urls.append(url)
                logger.info(f"Found Looker URL: {url}")

        return looker_urls

    def post_message(self, channel_id: str, text: str, thread_ts: str = None) -> bool:
        """
        Post a message to a channel or thread

        Args:
            channel_id: Channel ID
            text: Message text
            thread_ts: Thread timestamp (for replies)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            response = self.client.chat_postMessage(
                channel=channel_id,
                text=text,
                thread_ts=thread_ts
            )

            logger.info(f"Posted message to channel {channel_id}")
            return True

        except SlackApiError as e:
            logger.error(f"Error posting message: {e}")
            return False

    def send_dm(self, user_id: str, text: str) -> bool:
        """
        Send a direct message to a user

        Args:
            user_id: User ID
            text: Message text

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Open DM channel
            response = self.client.conversations_open(users=[user_id])
            dm_channel_id = response['channel']['id']

            # Send message
            self.client.chat_postMessage(
                channel=dm_channel_id,
                text=text
            )

            logger.info(f"Sent DM to user {user_id}")
            return True

        except SlackApiError as e:
            logger.error(f"Error sending DM: {e}")
            return False

    def parse_credit_request(self, message: Dict) -> Optional[Dict]:
        """
        Parse a message to determine if it's a credit request

        Args:
            message: Slack message dictionary

        Returns:
            Parsed request dict with Looker URL if valid, None otherwise

        Returns dict format:
            {
                'message_ts': '1234567890.123456',
                'channel_id': 'C123456',
                'text': 'original message text',
                'looker_url': 'https://looker.com/...',
                'user_id': 'U123456',
                'has_looker_link': True/False
            }
        """
        # Skip bot messages
        if message.get('bot_id') or message.get('subtype') == 'bot_message':
            return None

        text = message.get('text', '')
        message_ts = message.get('ts')
        user_id = message.get('user')

        # Extract Looker URLs
        looker_urls = self.extract_looker_urls(text)

        # If no Looker URL found, still return partial data
        # The orchestrator can decide if it needs to request a link
        return {
            'message_ts': message_ts,
            'text': text,
            'looker_url': looker_urls[0] if looker_urls else None,
            'user_id': user_id,
            'has_looker_link': len(looker_urls) > 0
        }


# Example usage
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    client = SlackClient()

    if client.test_connection():
        print("✅ Slack connection successful!")

        # Test channel lookup
        channel_name = Config.SLACK_TEST_CHANNEL
        channel_id = client.get_channel_id(channel_name)

        if channel_id:
            print(f"✅ Found channel #{channel_name}: {channel_id}")

            # Get recent messages
            messages = client.get_recent_messages(channel_id, limit=10)
            print(f"\n📨 Retrieved {len(messages)} recent messages")

            # Parse each message
            for i, msg in enumerate(messages, 1):
                parsed = client.parse_credit_request(msg)
                if parsed:
                    print(f"\nMessage {i}:")
                    print(f"  Timestamp: {parsed['message_ts']}")
                    print(f"  Has Looker Link: {parsed['has_looker_link']}")
                    if parsed['looker_url']:
                        print(f"  Looker URL: {parsed['looker_url']}")
        else:
            print(f"❌ Channel #{channel_name} not found")
    else:
        print("❌ Slack connection failed")
