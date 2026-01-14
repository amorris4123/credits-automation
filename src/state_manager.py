"""
State Manager
Tracks processed messages to avoid duplicate processing
Supports both local file storage and S3 backend
"""

import json
import logging
from pathlib import Path
from typing import Set, Dict, Any
from datetime import datetime
from .config import Config

logger = logging.getLogger(__name__)


class StateManager:
    """Manages bot state - tracks processed messages"""

    def __init__(self, state_file: Path = None):
        """
        Initialize state manager

        Args:
            state_file: Path to state file (defaults to Config)
        """
        self.state_file = state_file or Config.STATE_FILE
        self.use_s3 = Config.USE_S3_STORAGE
        self.aws_client = Config.get_aws_client() if self.use_s3 else None

        # Load state from S3 or local file
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """
        Load state from S3 or local file

        Returns:
            State dictionary
        """
        # Try S3 first if enabled
        if self.use_s3 and self.aws_client:
            try:
                content = self.aws_client.read_from_s3(
                    bucket=Config.S3_BUCKET,
                    key=Config.S3_STATE_KEY
                )
                if content:
                    state = json.loads(content)
                    logger.info(f"Loaded state from S3: s3://{Config.S3_BUCKET}/{Config.S3_STATE_KEY}")

                    # Also save to local file as cache
                    self._save_to_local_file(state)

                    return state
                else:
                    logger.info("No state file in S3, checking local cache")
            except Exception as e:
                logger.warning(f"Error loading state from S3: {e}, falling back to local file")

        # Fall back to local file
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                logger.info(f"Loaded state from local file: {self.state_file}")
                return state
            except Exception as e:
                logger.error(f"Error loading local state file: {e}")
                return self._create_empty_state()
        else:
            logger.info("No existing state, creating new state")
            return self._create_empty_state()

    def _create_empty_state(self) -> Dict[str, Any]:
        """Create empty state structure"""
        return {
            'processed_messages': [],
            'last_check_timestamp': None,
            'total_processed': 0,
            'created_at': datetime.now().isoformat()
        }

    def _save_to_local_file(self, state: Dict = None):
        """Save state to local file"""
        state_to_save = state or self.state
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state_to_save, f, indent=2)
            logger.debug(f"State saved to local file: {self.state_file}")
        except Exception as e:
            logger.error(f"Error saving local state: {e}")

    def _save_state(self):
        """Save current state to S3 and/or local file"""
        # Always save to local file (as cache/backup)
        self._save_to_local_file()

        # If S3 enabled, also save to S3
        if self.use_s3 and self.aws_client:
            try:
                content = json.dumps(self.state, indent=2)
                success = self.aws_client.write_to_s3(
                    bucket=Config.S3_BUCKET,
                    key=Config.S3_STATE_KEY,
                    content=content,
                    content_type='application/json'
                )
                if success:
                    logger.info(f"State saved to S3: s3://{Config.S3_BUCKET}/{Config.S3_STATE_KEY}")
                else:
                    logger.warning("Failed to save state to S3")
            except Exception as e:
                logger.error(f"Error saving state to S3: {e}")

    def is_processed(self, message_ts: str) -> bool:
        """
        Check if a message has been processed

        Args:
            message_ts: Slack message timestamp

        Returns:
            True if message has been processed, False otherwise
        """
        return message_ts in self.state['processed_messages']

    def mark_processed(self, message_ts: str, metadata: Dict = None):
        """
        Mark a message as processed

        Args:
            message_ts: Slack message timestamp
            metadata: Optional metadata about the processing
        """
        if not self.is_processed(message_ts):
            self.state['processed_messages'].append(message_ts)
            self.state['total_processed'] += 1

            # Store metadata if provided
            if metadata:
                if 'processing_details' not in self.state:
                    self.state['processing_details'] = {}
                self.state['processing_details'][message_ts] = {
                    **metadata,
                    'processed_at': datetime.now().isoformat()
                }

            self._save_state()
            logger.info(f"Marked message {message_ts} as processed")

    def update_last_check(self):
        """Update the last check timestamp"""
        self.state['last_check_timestamp'] = datetime.now().isoformat()
        self._save_state()

    def get_unprocessed_messages(self, messages: list) -> list:
        """
        Filter out already processed messages

        Args:
            messages: List of message dictionaries

        Returns:
            List of unprocessed messages
        """
        unprocessed = [
            msg for msg in messages
            if not self.is_processed(msg.get('ts'))
        ]

        logger.info(f"Found {len(unprocessed)} unprocessed messages out of {len(messages)} total")
        return unprocessed

    def get_stats(self) -> Dict[str, Any]:
        """
        Get processing statistics

        Returns:
            Dictionary with stats
        """
        return {
            'total_processed': self.state['total_processed'],
            'last_check': self.state['last_check_timestamp'],
            'created_at': self.state['created_at'],
            'processed_count': len(self.state['processed_messages'])
        }

    def cleanup_old_entries(self, days_to_keep: int = 30):
        """
        Remove old processed message entries to keep file size manageable

        Args:
            days_to_keep: Number of days of history to keep
        """
        # Keep at least the last N messages
        max_entries = 1000

        if len(self.state['processed_messages']) > max_entries:
            # Keep only the most recent entries
            self.state['processed_messages'] = self.state['processed_messages'][-max_entries:]

            # Also cleanup processing details if they exist
            if 'processing_details' in self.state:
                kept_ts = set(self.state['processed_messages'])
                self.state['processing_details'] = {
                    k: v for k, v in self.state['processing_details'].items()
                    if k in kept_ts
                }

            self._save_state()
            logger.info(f"Cleaned up old state entries, keeping {max_entries} most recent")


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    manager = StateManager()

    # Print current stats
    stats = manager.get_stats()
    print("State Manager Stats:")
    print(f"  Total Processed: {stats['total_processed']}")
    print(f"  Last Check: {stats['last_check']}")
    print(f"  Created At: {stats['created_at']}")

    # Test marking a message as processed
    test_ts = "1234567890.123456"
    print(f"\nIs {test_ts} processed? {manager.is_processed(test_ts)}")

    manager.mark_processed(test_ts, {'test': True, 'credit_amount': 179.73})
    print(f"Is {test_ts} processed now? {manager.is_processed(test_ts)}")

    # Update last check
    manager.update_last_check()
    print(f"\nUpdated last check timestamp")
