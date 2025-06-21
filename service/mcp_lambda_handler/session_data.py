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

"""Session data classes for the MCP Lambda handler."""

from typing import Any, Dict, Generic, TypeVar

T = TypeVar('T')


class SessionData(Generic[T]):
    """Helper class for type-safe session data access."""

    def __init__(self, data: Dict[str, Any]):
        """Initialize the class."""
        self._data = data

    def get(self, key: str, default: T = None) -> T:
        """Get a value from session data with type safety."""
        return self._data.get(key, default)

    def set(self, key: str, value: T) -> None:
        """Set a value in session data."""
        self._data[key] = value

    def raw(self) -> Dict[str, Any]:
        """Get the raw dictionary data."""
        return self._data
