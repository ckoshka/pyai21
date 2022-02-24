This is a simple async Python wrapper for AI21's API. It also comes with a convenient decorator function (@interpret) that sends the returned result of a function to that API, with the provided keyword args.

Example of @interpret in action:

```python
@interpret(stops=['"""'])
async def answer_anything(question: str) -> str:
    return f"""
    from instant_answers import SemanticQuery
    querier = SemanticQuery(minimum_length=250, rank_by='upvotes', moderator_curated=True)
    question = "{question}"
    querier.get_answer(question)
    # You should get this thorough answer:
    # \"\"\""""

await answer_anything(question="Why did the French Revolution occur?")

    # "Revolutions can fundamentally transform the political, social, and economic structures of a..."

@interpret(stops=["']", "]"], count=10)
async def name_generator(kwargs: str) -> str:
    return f"""
    from names import generate_names
    generate_names(nationality="Korean", script="Latin", surname=True, seed=2031, count=1, quality="high")
    # Should return: ['Byung Soo Kim']
    # generate_names({kwargs}, seed=2031)
    # Should return: ['"""

await name_generator(kwargs='nationality="Singaporean", script="Latin", rareness="common"') 

    # "['Joh Jae Lin', 'James Yi Jin Hao', ..."
```

Generally fictional Python code works much better than natural language, in addition to being more concise.

# Usage

```bash
pip install pyai21
```

You'll need to have a .env file in your current working directory with the following variables:
```
AI21_API_KEY_FILE=your_api_key_file.txt # this should be a newline separated list of keys
POOL_KEY=skjhjfkhsk # optional: ignore this if you're not on the Personate discord server
```
Based on which of these are specified, it will return different functions. You can override this by importing get_ai21 or get_pool directly. The end results should be the same, however.

## get

```python
result = await get(
    prompt="Here are my top ten favourite things about Python: 1.", 
    stops=["10"],
    max=100,
    temp=0.85,
    top_p=1.0,
    size="j1-large",
    count=2,
    presence_penalty=0.2,
    count_penalty=0.2,
    frequency_penalty=20.0,
    banned_tokens=["type", "safety"],
    logit_biases={"shared": -10, "mutable": -0.5, "references": -50},
    key=None
)

# You can optionally specify a particular key if you're using ai21.
```

## emit

This shows you the top 64 most likely tokens that might follow after your prompt.

```python
result = await emit(prompt="Death is just the next", size="j1-jumbo")
#{ "token": "\u2581adventure", "logprob": -6.043289661407471 },
```

## match

```python
options = ["custard", "chocolate sauce", "eggnog", "sprinkles"]
top = await match(prompt="The best desert topping is", top=1, available_options=options, size="j1-jumbo")
```