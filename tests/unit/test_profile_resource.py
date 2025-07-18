from service.logic.resources.profiles import get_profile_by_id


def test_get_profile_by_id_returns_correct_format():
    """Test that get_profile_by_id returns a dictionary with correct keys."""
    user_id = 123
    result = get_profile_by_id(user_id)

    assert isinstance(result, dict)
    assert 'name' in result
    assert 'status' in result
    assert result['status'] == 'active'
