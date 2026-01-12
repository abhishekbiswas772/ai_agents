from clients.llm_client import LLMClient
import asyncio

async def main():
    client = LLMClient()
    async for event in client.chat_completion(
        messages=[
            {
                "role" : "user",
                "content" : "whats app"
            }
        ],
        stream=True
    ):
        print(event)
    print("DONE")

if __name__ == "__main__":
    asyncio.run(main())

    