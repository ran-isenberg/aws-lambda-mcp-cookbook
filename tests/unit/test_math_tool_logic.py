from service.logic.tools.math import add_two_numbers


def test_add_two_numbers_positive():
    assert add_two_numbers(2, 3) == 5


def test_add_two_numbers_negative():
    assert add_two_numbers(-2, -3) == -5


def test_add_two_numbers_mixed_sign():
    assert add_two_numbers(-2, 3) == 1
    assert add_two_numbers(2, -3) == -1


def test_add_two_numbers_zero():
    assert add_two_numbers(0, 0) == 0
    assert add_two_numbers(0, 5) == 5
    assert add_two_numbers(5, 0) == 5


def test_add_two_numbers_large():
    assert add_two_numbers(10**6, 10**6) == 2 * 10**6
