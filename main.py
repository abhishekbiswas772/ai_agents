from typing import Any, Dict
from clients.llm_client import LLMClient
import asyncio
import click


class CLI:
    def __init__(self):
        pass

    def run_single(self):
        pass 

async def run(messages : Dict[str, Any]):
    client = LLMClient()
    async for event in client.chat_completion(
        messages=messages,
        stream=True
    ):
        print(event)
    print("DONE")

@click.command()
@click.argument("prompt", required=False)
def main(prompt : str | None):
    print(prompt)
    messages = [{
        "role" : "user",
        "content" : prompt
    }]
    asyncio.run(run(messages=messages))
    

if __name__ == "__main__":
    main()

    