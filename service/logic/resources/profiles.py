def get_profile_by_id(user_id: int) -> dict[str, str]:
    return {'name': f'User {user_id}', 'status': 'active'}
