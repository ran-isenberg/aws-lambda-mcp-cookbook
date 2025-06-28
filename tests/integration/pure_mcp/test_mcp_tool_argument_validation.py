import unittest
from enum import Enum
from typing import Dict, List, Optional

from service.mcp_lambda_handler.mcp_lambda_handler import MCPLambdaHandler
from service.mcp_lambda_handler.session import DynamoDBSessionStore
from tests.integration.conftest import table_name


class TestEnum(Enum):
    """Test enum for argument validation."""

    VALUE1 = 'value1'
    VALUE2 = 'value2'
    NUMBER_VALUE = 42


class ToolArgumentValidationTest(unittest.TestCase):
    """Test cases for tool argument validation."""

    def setUp(self):
        """Set up test environment."""
        self.handler = MCPLambdaHandler(
            name='test',
            version='1.0.0',
            session_store=DynamoDBSessionStore(table_name_getter=lambda: table_name),
        )
        self.handler.session_id = 'test-session'  # Set a session ID for error responses
        self.handler.request_id = 'test-request-id'  # Set a request ID for error responses

    def test_primitive_conversion(self):
        """Test conversion of primitive types."""

        # Define a test function with primitive types
        def test_func(int_arg: int, float_arg: float, bool_arg: bool, str_arg: str):
            pass

        # Test successful conversion
        args = {
            'int_arg': '42',  # String that should convert to int
            'float_arg': '3.14',  # String that should convert to float
            'bool_arg': 'true',  # String that should convert to bool
            'str_arg': 123,  # Number that should convert to string
        }

        converted, error = self.handler._validate_tool_args('test_func', args, test_func)
        self.assertIsNone(error, 'Conversion should succeed without error')
        self.assertEqual(converted['int_arg'], 42)
        self.assertEqual(converted['float_arg'], 3.14)
        self.assertTrue(converted['bool_arg'])
        self.assertEqual(converted['str_arg'], '123')  # Should remain as-is (no need to convert numeric to string)

        # Test various boolean representations
        for true_value in ['true', 'True', 'yes', 'Yes', '1', 'on', 'On']:
            args = {'bool_arg': true_value, 'int_arg': 1, 'float_arg': 1.0, 'str_arg': 'test'}
            converted, _ = self.handler._validate_tool_args('test_func', args, test_func)
            self.assertTrue(converted['bool_arg'], f'{true_value} should convert to True')

        for false_value in ['false', 'False', 'no', 'No', '0', 'off', 'Off']:
            args = {'bool_arg': false_value, 'int_arg': 1, 'float_arg': 1.0, 'str_arg': 'test'}
            converted, _ = self.handler._validate_tool_args('test_func', args, test_func)
            self.assertFalse(converted['bool_arg'], f'{false_value} should convert to False')

        # Test invalid conversions
        args = {'int_arg': 'not-an-int', 'float_arg': 1.0, 'bool_arg': True, 'str_arg': 'test'}
        _, error = self.handler._validate_tool_args('test_func', args, test_func)
        self.assertIsNotNone(error, 'Should return error for invalid int conversion')

        args = {'int_arg': 1, 'float_arg': 'not-a-float', 'bool_arg': True, 'str_arg': 'test'}
        _, error = self.handler._validate_tool_args('test_func', args, test_func)
        self.assertIsNotNone(error, 'Should return error for invalid float conversion')

        args = {'int_arg': 1, 'float_arg': 1.0, 'bool_arg': 'not-a-bool', 'str_arg': 'test'}
        _, error = self.handler._validate_tool_args('test_func', args, test_func)
        self.assertIsNotNone(error, 'Should return error for invalid bool conversion')

    def test_enum_conversion(self):
        """Test conversion of enum types."""

        # Define a test function with an enum parameter
        def test_func(enum_arg: TestEnum):
            pass

        # Test valid enum value
        args = {'enum_arg': 'value1'}
        converted, error = self.handler._validate_tool_args('test_func', args, test_func)
        self.assertIsNone(error, 'Conversion should succeed without error')
        self.assertEqual(converted['enum_arg'], TestEnum.VALUE1)

        # Test numeric enum value
        args = {'enum_arg': 42}
        converted, error = self.handler._validate_tool_args('test_func', args, test_func)
        self.assertIsNone(error, 'Conversion should succeed without error')
        self.assertEqual(converted['enum_arg'], TestEnum.NUMBER_VALUE)

        # Test case-insensitive enum name match
        args = {'enum_arg': 'VALUE1'}
        converted, error = self.handler._validate_tool_args('test_func', args, test_func)
        self.assertIsNone(error, 'Conversion should succeed without error')
        self.assertEqual(converted['enum_arg'], TestEnum.VALUE1)

        # Test invalid enum value
        args = {'enum_arg': 'invalid-value'}
        _, error = self.handler._validate_tool_args('test_func', args, test_func)
        self.assertIsNotNone(error, 'Should return error for invalid enum value')

    def test_list_conversion(self):
        """Test conversion of list types."""

        # Define a test function with a list parameter
        def test_func(list_arg: List[str]):
            pass

        # Test existing list
        args = {'list_arg': ['item1', 'item2']}
        converted, error = self.handler._validate_tool_args('test_func', args, test_func)
        self.assertIsNone(error, 'Conversion should succeed without error')
        self.assertEqual(converted['list_arg'], ['item1', 'item2'])

        # Test single value to list conversion
        args = {'list_arg': 'single-item'}
        converted, error = self.handler._validate_tool_args('test_func', args, test_func)
        self.assertIsNone(error, 'Conversion should succeed without error')
        self.assertEqual(converted['list_arg'], ['single-item'])

    def test_dict_conversion(self):
        """Test conversion of dictionary types."""

        # Define a test function with a dict parameter
        def test_func(dict_arg: Dict[str, int]):
            pass

        # Test valid dict
        args = {'dict_arg': {'key1': 1, 'key2': 2}}
        converted, error = self.handler._validate_tool_args('test_func', args, test_func)
        self.assertIsNone(error, 'Conversion should succeed without error')
        self.assertEqual(converted['dict_arg'], {'key1': 1, 'key2': 2})

        # Test invalid dict
        args = {'dict_arg': 'not-a-dict'}
        _, error = self.handler._validate_tool_args('test_func', args, test_func)
        self.assertIsNotNone(error, 'Should return error for invalid dict value')

    def test_optional_conversion(self):
        """Test conversion of optional types."""

        # Define a test function with optional parameters
        def test_func(opt_int: Optional[int], opt_enum: Optional[TestEnum]):
            pass

        # Test None values
        args = {'opt_int': None, 'opt_enum': None}
        converted, error = self.handler._validate_tool_args('test_func', args, test_func)
        self.assertIsNone(error, 'Conversion should succeed without error')
        self.assertIsNone(converted['opt_int'])
        self.assertIsNone(converted['opt_enum'])

        # Test valid values
        args = {'opt_int': '42', 'opt_enum': 'value2'}
        converted, error = self.handler._validate_tool_args('test_func', args, test_func)
        self.assertIsNone(error, 'Conversion should succeed without error')
        self.assertEqual(converted['opt_int'], 42)
        self.assertEqual(converted['opt_enum'], TestEnum.VALUE2)

        # Test invalid values
        args = {'opt_int': 'not-an-int', 'opt_enum': 'value2'}
        _, error = self.handler._validate_tool_args('test_func', args, test_func)
        self.assertIsNotNone(error, 'Should return error for invalid int conversion')

    def test_missing_required_params(self):
        """Test validation of missing required parameters."""

        # Define a test function with required parameters
        def test_func(required_arg: str, optional_arg: Optional[str] = None):
            pass

        # Test missing required parameter
        args = {'optional_arg': 'value'}
        _, error = self.handler._validate_tool_args('test_func', args, test_func)
        self.assertIsNotNone(error, 'Should return error for missing required parameter')
        self.assertIn('Missing required parameters', error['body'])

        # Test all parameters present
        args = {'required_arg': 'value', 'optional_arg': 'optional'}
        converted, error = self.handler._validate_tool_args('test_func', args, test_func)
        self.assertIsNone(error, 'Conversion should succeed without error')
        self.assertEqual(converted['required_arg'], 'value')
        self.assertEqual(converted['optional_arg'], 'optional')

    def test_unexpected_params(self):
        """Test handling of unexpected parameters."""

        # Define a test function with specific parameters
        def test_func(arg1: str, arg2: int):
            pass

        # Test with unexpected parameter
        args = {'arg1': 'value', 'arg2': 42, 'unexpected': 'extra'}
        converted, error = self.handler._validate_tool_args('test_func', args, test_func)
        self.assertIsNone(error, 'Conversion should succeed without error')
        self.assertEqual(converted['arg1'], 'value')
        self.assertEqual(converted['arg2'], 42)
        self.assertNotIn('unexpected', converted, 'Unexpected parameter should be removed')


if __name__ == '__main__':
    unittest.main()
