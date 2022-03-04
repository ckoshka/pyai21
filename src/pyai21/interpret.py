from pyai21.completions import get
from typing import Callable, Union, List

from textwrap import dedent
def interpret(**kwargs_for_get) -> Callable:
    '''This is a decorator that reads the return value, and formats it using its arguments like so:

    @interpret(**kwargs_for_get)
    def generate_pizza_name(culture: str) -> str:
        return f"""My favourite {culture} pizza is"""
    '''
    if not kwargs_for_get.pop('temp', False):
        kwargs_for_get['temp'] = 0.83
    if not kwargs_for_get.pop('frequency_penalty', False):
        kwargs_for_get['frequency_penalty'] = 0.2
    if not kwargs_for_get.pop('stops', False):
        kwargs_for_get['stops'] = ["\n"]
    def outer_wrapper(func: Callable) -> Callable:
        async def inner_wrapper(*args, **kwargs) -> Union[str, List[str]]:
            prompt = await func(*args, **kwargs)
            prompt = dedent(prompt) #type: ignore
            return await get(prompt, **kwargs_for_get)
        inner_wrapper.__doc__ = func.__doc__
        inner_wrapper.__annotations__ = func.__annotations__
        inner_wrapper.__name__ = func.__name__
        return inner_wrapper
    return outer_wrapper