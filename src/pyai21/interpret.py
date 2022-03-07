from pyai21.completions import get
from typing import Any, AsyncGenerator, Callable, Optional, Union, List
from textwrap import dedent
from ast import literal_eval
import regex as re


def regularise(inner_wrapper: Callable, func: Callable) -> Callable:
    inner_wrapper.__doc__ = func.__doc__
    inner_wrapper.__annotations__ = func.__annotations__
    inner_wrapper.__name__ = func.__name__
    return inner_wrapper


def interpret(**kwargs_for_get) -> Callable:
    '''This is a decorator that reads the return value, and formats it using its arguments like so:

    @interpret(**kwargs_for_get)
    def generate_pizza_name(culture: str) -> str:
        return f"""My favourite {culture} pizza is"""
    '''
    default_kwargs = {"temp": 0.83, "frequency_penalty": 0.2, "stops": ["\n"]}
    default_kwargs.update(kwargs_for_get)

    def outer_wrapper(func: Callable) -> Callable:
        async def inner_wrapper(*args, **kwargs) -> Union[str, List[str]]:
            prompt = await func(*args, **kwargs)
            prompt = dedent(prompt)  # type: ignore
            return await get(prompt=prompt, **kwargs_for_get)

        return regularise(inner_wrapper, func)

    return outer_wrapper


def multistep(**kwargs_for_get) -> Callable:
    default_kwargs = {"temp": 0.83, "frequency_penalty": 0.2, "stops": ["\n"]}
    default_kwargs.update(kwargs_for_get)
    """Example:
    hello my name is {[' ']} and my favourite color is {[' ', '.']}
    In this case, everything between the braces would be captured and parsed as a list of stops via ast's literal_eval."""

    def outer_wrapper(func: Callable) -> Callable:
        async def inner_wrapper(*args, **kwargs) -> str:
            prompt = await func(*args, **kwargs)
            stop_rules: List[str] = re.findall(r"\{(.*?)\}", prompt)
            stop_rules_lists: List[List[str]] = [
                literal_eval(rule) for rule in stop_rules
            ]
            steps: List[str] = re.split(r"{[^}]*}", prompt)
            dynamic_prompt = ""
            for step, rule in zip(steps, stop_rules_lists):
                dynamic_prompt += step
                result = await get(prompt=step, **kwargs_for_get, stops=rule)
                if isinstance(result, str):
                    dynamic_prompt += result
                else:
                    dynamic_prompt += result[0]
            return dynamic_prompt

        return regularise(inner_wrapper, func)

    return outer_wrapper


# This decorator turns normal functions into async generators. It appends sent values using a separator to the prompt, calls get on the prompt, appends that to the string, and yields the result.

from loguru import logger

"""We could do this:
gen = shopping_list_generator(diet="vegetarian")
await gen.asend(None)
new_item = await gen.asend("2. Sunflower oil")
await gen.__anext__()
new_item2 = await gen.asend("4. Lots of love from grandma")

But it would be simpler to create an object with a send method that handles this logic for us."""


class GeneratorManager:
    @classmethod
    def generate(
        cls, separator: str = "\n", maximum_length: int = 10, **kwargs_for_get
    ):
        default_kwargs = {"temp": 0.83, "frequency_penalty": 0.2, "stops": ["\n"]}
        default_kwargs.update(kwargs_for_get)

        def outer_wrapper(func: Callable) -> GeneratorManager:
            async def inner_wrapper(
                *args, **kwargs
            ) -> AsyncGenerator[Union[str, None], str]:
                appended_items = []
                prompt = func(*args, **kwargs)
                logger.debug(f"Prompt: {prompt}")
                prompt = dedent(prompt)
                while True:
                    value = yield
                    logger.debug(f"Value: {value}")
                    if value:
                        appended_items.append(value)
                    logger.debug(f"Appended items: {appended_items}")
                    logger.debug(
                        f"Final prompt: {prompt + separator + separator.join(appended_items) + separator}"
                    )
                    result = await get(
                        prompt=prompt
                        + separator
                        + separator.join(appended_items[-maximum_length:])
                        + separator,
                        **kwargs_for_get,
                    )
                    logger.debug(f"Result: {result}")
                    if isinstance(result, str):
                        appended_items.append(result)
                        logger.debug(f"Appended items after result: {appended_items}")
                        yield result
                    else:
                        appended_items.append(result[0])
                        yield result[0]

            return cls(regularise(inner_wrapper, func))

        return outer_wrapper

    def __init__(self, func: Callable):
        self.func = func
        self.generator: Optional[AsyncGenerator] = None

    def __call__(self, *args, **kwargs):
        self.generator = self.func(*args, **kwargs)
        return self

    async def send(self, value: str):
        if not self.generator:
            return None
        await self.generator.__anext__()
        return await self.generator.asend(value)


generate = GeneratorManager.generate
