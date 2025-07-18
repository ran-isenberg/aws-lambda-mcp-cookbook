from service.handlers.utils.observability import logger


def add_two_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    logger.info('Adding two numbers', extra={'a': a, 'b': b})
    return a + b
