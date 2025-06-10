# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
## Taken from https://github.com/awslabs/mcp/tree/main/src/mcp-lambda-handler
"""Session management for MCP server with pluggable storage."""

import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional

from boto3 import resource as boto3_resource

from service.handlers.utils.observability import logger


class SessionStore(ABC):
    """Abstract base class for session storage implementations."""

    @abstractmethod
    def create_session(self, session_data: Optional[Dict[str, Any]] = None) -> str:
        """Create a new session.

        Args:
            session_data: Optional initial session data

        Returns:
            The session ID

        """
        pass

    @abstractmethod
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data.

        Args:
            session_id: The session ID to look up

        Returns:
            Session data or None if not found

        """
        pass

    @abstractmethod
    def update_session(self, session_id: str, session_data: Dict[str, Any]) -> bool:
        """Update session data.

        Args:
            session_id: The session ID to update
            session_data: New session data

        Returns:
            True if successful, False otherwise

        """
        pass

    @abstractmethod
    def delete_session(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: The session ID to delete

        Returns:
            True if successful, False otherwise

        """
        pass


class NoOpSessionStore(SessionStore):
    """A no-op session store that doesn't actually store sessions."""

    def create_session(self, session_data: Optional[Dict[str, Any]] = None) -> str:
        """Create a new session ID but don't store anything."""
        return str(uuid.uuid4())

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Return an empty session data."""
        return {}

    def update_session(self, session_id: str, session_data: Dict[str, Any]) -> bool:
        """Pretend to update but do nothing."""
        return True

    def delete_session(self, session_id: str) -> bool:
        """Pretend to delete but do nothing."""
        return True


class DynamoDBSessionStore(SessionStore):
    """Manages MCP sessions using DynamoDB."""

    def __init__(self, table_name_getter: Callable[[], str]):
        """Initialize the session store.

        Args:
            table_name_getter: A callable that takes no arguments and returns the DynamoDB table name as a string

        """
        self.table_name_getter = table_name_getter
        self._table = None
        self._dynamodb = None

    @property
    def table_name(self) -> str:
        """Get the table name by calling the table_name_getter."""
        return self.table_name_getter()

    @property
    def dynamodb(self):
        """Lazy initialization of the DynamoDB resource."""
        if self._dynamodb is None:
            self._dynamodb = boto3_resource('dynamodb')
        return self._dynamodb

    @property
    def table(self):
        """Lazy initialization of the DynamoDB table."""
        if self._table is None:
            self._table = self.dynamodb.Table(self.table_name)  # pyright: ignore [reportAttributeAccessIssue]
        return self._table

    def create_session(self, session_data: Optional[Dict[str, Any]] = None) -> str:
        """Create a new session.

        Args:
            session_data: Optional initial session data

        Returns:
            The session ID

        """
        # Generate a secure random UUID for the session
        session_id = str(uuid.uuid4())

        # Set session expiry to 24 hours from now
        expires_at = int(time.time()) + (24 * 60 * 60)

        # Store session in DynamoDB
        item = {
            'session_id': session_id,
            'expires_at': expires_at,
            'created_at': int(time.time()),
            'data': session_data or {},
        }

        self.table.put_item(Item=item)
        logger.info(f'Created session {session_id}')

        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data.

        Args:
            session_id: The session ID to look up

        Returns:
            Session data or None if not found

        """
        try:
            response = self.table.get_item(Key={'session_id': session_id})
            item = response.get('Item')

            if not item:
                return None

            # Check if session has expired
            if item.get('expires_at', 0) < time.time():
                self.delete_session(session_id)
                return None

            return item.get('data', {})

        except Exception as e:
            logger.error(f'Error getting session {session_id}: {e}')
            return None

    def update_session(self, session_id: str, session_data: Dict[str, Any]) -> bool:
        """Update session data.

        Args:
            session_id: The session ID to update
            session_data: New session data

        Returns:
            True if successful, False otherwise

        """
        try:
            self.table.update_item(
                Key={'session_id': session_id},
                UpdateExpression='SET #data = :data',
                ExpressionAttributeNames={'#data': 'data'},
                ExpressionAttributeValues={':data': session_data},
            )
            return True
        except Exception as e:
            logger.error(f'Error updating session {session_id}: {e}')
            return False

    def delete_session(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: The session ID to delete

        Returns:
            True if successful, False otherwise

        """
        try:
            self.table.delete_item(Key={'session_id': session_id})
            logger.info(f'Deleted session {session_id}')
            return True
        except Exception as e:
            logger.error(f'Error deleting session {session_id}: {e}')
            return False
