"""
State Manager
Tracks processed messages to avoid duplicate processing
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
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """
        Load state from file

        Returns:
            State dictionary
        """
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                logger.info(f"Loaded state from {self.state_file}")
                return state
            except Exception as e:
                logger.error(f"Error loading state file: {e}")
                return self._create_empty_state()
        else:
            logger.info("No existing state file, creating new state")
            return self._create_empty_state()

    def _create_empty_state(self) -> Dict[str, Any]:
        """Create empty state structure"""
        return {
            'processed_messages': [],
            'last_check_timestamp': None,
            'total_processed': 0,
            'created_at': datetime.now().isoformat()
        }

    def _save_state(self):
        """Save current state to file"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
            logger.debug(f"State saved to {self.state_file}")
        except Exception as e:
            logger.error(f"Error saving state: {e}")

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
