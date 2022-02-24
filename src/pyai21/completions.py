WHITESPACE_CHARACTER = "▁"
from typing import Generator, List, Dict, Union, Tuple
import random
import ujson
import aiohttp
import json
from rapidfuzz import cpp_fuzz, cpp_process
#API: >> process.extractOne("cowboys", choices, scorer=fuzz.WRatio)
#("Dallas Cowboys", 90, 3)
from loguru import logger

from dotenv import load_dotenv
load_dotenv()
import os

THE_POOL_URL = "https://thepool.glossandra.repl.co"

AI21_API_KEY_FILE = os.environ.get("AI21_API_KEY_FILE", None)
POOL_KEY = os.environ.get("POOL_KEY", None)

def get_api_key() -> Generator[str, None, None]:
    '''Yields keys in a cyclic loop.'''
    if AI21_API_KEY_FILE:
        with open(AI21_API_KEY_FILE, "r") as f:
            keys = f.read().split("\n")
        random.shuffle(keys)
        while True:
            for key in keys:
                yield key

KEY_GENERATOR = get_api_key()

async def get_ai21(
    prompt: str,
    stops: list = None,
    max: int = 100,
    temp: float = 0.85,
    top_p: float = 1.0,
    size: str = "j1-jumbo",
    count: int = 1,
    presence_penalty: float = 0.0,
    count_penalty: float = 0.0,
    frequency_penalty: float = 0.0,
    banned_tokens: List[str] = None,
    logit_biases: Dict[str, float] = dict(),
    key: str = None,
) -> Union[str, List[str]]:
    '''Takes a prompt and returns a completed response by J1-Jumbo.
    :param prompt: The prompt to get the text of.
    :param stops: A list of strings to stop at.
    :param max: The maximum number of tokens to return.
    :param temp: The temperature to use.
    :param top_p: The top_p to use – this is more complicated, just ignore it.
    :param size: The size of the model to use.
    :param count: The number of separate completions to return.
    :param presence_penalty: The penalty to apply to specific words. Negative means it's less likely to be chosen.
    :param count_penalty: The penalty to apply to the number of tokens. Range 0.0 to 1.0, 0.33 is a good value.
    :param frequency_penalty: The penalty to apply to the frequency of tokens. Range 0.0 to 1.0, 0.23 is a good value. Any higher and it will penalise newline chars, so keep that in mind.
    :param banned_tokens: A list of tokens to ban.
    :param logit_biases: A dictionary of tokens to logit biases (how likely you want tokens to be).'''
    json_body = {
        "prompt": prompt,
        "numResults": count,
        "maxTokens": max,
        "topKReturn": 0,
        "temperature": temp,
        "topP": top_p,
        "presencePenalty": {'scale': presence_penalty},
        "countPenalty": {'scale': count_penalty},
        "frequencyPenalty": {'scale': frequency_penalty},
    }
    logger.debug(f"Sending request to AI21 with body: {json_body}")
    if stops:
        json_body["stopSequences"] = stops
    if banned_tokens:
        for token in banned_tokens:
            new_token = token.replace(" ", WHITESPACE_CHARACTER)
            logit_biases.update({
                new_token: -1000,
                new_token + WHITESPACE_CHARACTER: -1000,
                WHITESPACE_CHARACTER + new_token: -1000
            })
    async with aiohttp.ClientSession(
        json_serialize=ujson.dumps) as session:
        if not key:
            key = next(KEY_GENERATOR)
        logger.debug(f"Awaiting response using {key}")
        async with session.post(
            f"https://api.ai21.com/studio/v1/{size}/complete",
            headers={"Authorization": f"Bearer {key}"},
            json=json_body
        ) as resp:
            logger.debug(f"Response received: {resp.content}")
            json_response_text = await resp.text()
    #logger.debug(f"JSON response: {json_response_text}")
    json_response = ujson.loads(json_response_text)
    #logger.info(f"Got response: {json_response}")
    completions: List[str] = []
    for compl in json_response['completions']:
        completions.append(compl['data']['text'])
    logger.debug(f"Received completions: {completions}")
    if len(completions) == 1:
        return completions[0]
    else:
        return completions

#@RATE_LIMITER.ratelimit_decorator
async def emit_ai21(
    prompt: str,
    size: str = "j1-jumbo",
    key: str = None,
) -> List[Dict[str, Union[str, float]]]:
    '''Takes a prompt and returns a list of tokens along with their logprobs.
    :param prompt: The prompt to get the text of.
    :param size: The size of the model to use. Can either be j1-large or j1-jumbo.'''
    json_body = {
        "prompt": prompt,
        "numResults": 1,
        "maxTokens": 1,
        "topKReturn": 64,
        "temperature": 0,
    }
    if not key:
        key = next(KEY_GENERATOR)
    async with aiohttp.ClientSession(
        json_serialize=ujson.dumps) as session:
        async with session.post(
            f"https://api.ai21.com/studio/v1/{size}/complete",
            headers={"Authorization": f"Bearer {key}"},
            json=json_body,
        ) as resp:
            json_response = await resp.json()
    top_k_tokens = json_response['completions'][0]['data']['tokens'][0]['topTokens']
    #Each has the form:
    #{ "token": "\u2581Jeff", "logprob": -6.043289661407471 },
    return top_k_tokens

async def get_pool(
    prompt: str,
    stops: list = None,
    max: int = 100,
    temp: float = 0.85,
    top_p: float = 1.0,
    size: str = "j1-jumbo",
    count: int = 1,
    presence_penalty: float = 0.0,
    count_penalty: float = 0.0,
    frequency_penalty: float = 0.0,
    banned_tokens: List[str] = None,
    logit_biases: Dict[str, float] = dict(),
) -> Union[str, List[str]]:
    '''Takes a prompt and returns a completed response by J1-Jumbo.
    :param prompt: The prompt to get the text of.
    :param stops: A list of strings to stop at.
    :param max: The maximum number of tokens to return.
    :param temp: The temperature to use.
    :param top_p: The top_p to use – this is more complicated, just ignore it.
    :param size: The size of the model to use.
    :param count: The number of separate completions to return.
    :param presence_penalty: The penalty to apply to specific words. Negative means it's less likely to be chosen.
    :param count_penalty: The penalty to apply to the number of tokens. Range 0.0 to 1.0, 0.33 is a good value.
    :param frequency_penalty: The penalty to apply to the frequency of tokens. Range 0.0 to 1.0, 0.23 is a good value. Any higher and it will penalise newline chars, so keep that in mind.
    :param banned_tokens: A list of tokens to ban.
    :param logit_biases: A dictionary of tokens to logit biases (how likely you want tokens to be).'''
    # This just serialises the kwargs into a json body and sends them to THE_POOL_URL + "/get" as a POST request.
    if max > 1600:
        raise ValueError("Please try and keep max tokens under 1600, the Pool is a limited resource!!")
    if count > 3:
        raise ValueError("Please try and keep count under 3, the Pool is a limited resource!!")
    json_body = {
        "prompt": prompt,
        "stops": stops,
        "max": max,
        "temp": temp,
        "top_p": top_p,
        "size": size,
        "count": count,
        "presence_penalty": presence_penalty,
        "count_penalty": count_penalty,
        "frequency_penalty": frequency_penalty,
        "banned_tokens": banned_tokens,
        "logit_biases": logit_biases,
        "key": POOL_KEY,
    }
    async with aiohttp.ClientSession(
        json_serialize=ujson.dumps) as session:
        async with session.post(
            THE_POOL_URL + "/get",
            json=json_body,
        ) as resp:
            try:
                json_response = await resp.json()
            except:
                logger.error(f"Error getting response from pool: {await resp.text()}")
                raise ValueError("Error getting response from pool")
    return json_response

async def emit_pool(
    prompt: str,
    size: str = "j1-jumbo",
) -> List[Dict[str, Union[str, float]]]:
    '''Takes a prompt and returns a list of tokens along with their logprobs.
    :param prompt: The prompt to get the text of.
    :param size: The size of the model to use. Can either be j1-large or j1-jumbo.'''
    # This also uses The Pool
    json_body = {
        "prompt": prompt,
        "size": size,
        "key": POOL_KEY,
    }
    async with aiohttp.ClientSession(
        json_serialize=ujson.dumps) as session:
        async with session.post(
            THE_POOL_URL + "/emit",
            json=json_body,
        ) as resp:
            json_response = await resp.json()
    return json_response
if AI21_API_KEY_FILE:
    get = get_ai21
    emit = emit_ai21
elif POOL_KEY:
    get = get_pool
    emit = emit_pool
else:
    raise ValueError("It looks like there's no .env file containing POOL_KEY or AI21_API_KEY_FILE. If you would like a key to The Pool, please join the discord server linked on the repo page for Personate. If you need an AI21 key, then you can get them here: https://studio.ai21.com/sign-up")

async def match(
    prompt: str,
    top: int,
    available_options: List[str],
    size: str = "j1-jumbo",
) -> List[str]:
    '''Matches a string list of options to the continuations predicted by a given prompt.
    e.g if the prompt is "What is the capital of France?" and the options are ["Paris", "Lyon", "Marseille"]
    then you'll get "Paris" first.
    :param prompt: The prompt to get the text of.
    :param top: The number of options to return.
    :param available_options: The list of options to match against.
    :param size: The size of the model to use. Can either be j1-large or j1-jumbo.'''
    tokens_as_list_of_dicts = await emit(prompt, size)
    tokens_as_dict: Dict[str, float] = {
        token['token'].replace("\u2581", ""): token['logprob'] #type: ignore
        for token in tokens_as_list_of_dicts
    }
    ranked_options: List[Tuple[str, float]] = []
    for option in available_options:
        #If the top result has a match higher than 86, we put it into ranked_options. Otherwise we ignore it
        top_result = cpp_process.extractOne(option, tokens_as_dict.keys(), scorer=cpp_fuzz.partial_token_set_ratio)
        if top_result[1] >= 76:
            new_tuple = (option, tokens_as_dict[top_result[0]])
            ranked_options.append(new_tuple)
    ranked_options.sort(key=lambda x: x[1], reverse=True)
    return [option[0] for option in ranked_options[:top]]
#res = emit("Hello, my name is", "j1-large")
#Pretty-print the results
#print(json.dumps(res, indent=2))
#options = ["George", "Kelly", "Peter", "Trump", "Melissa", "David"]
#print(match("Hello, my name is", 4, options))