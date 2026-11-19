import httpx
import asyncio

API_URL = "https://jsonplaceholder.typicode.com/posts/1"


def fetch_data(client: httpx.AsyncClient):
    response = client.get(API_URL, timeout=5.0)
    response.raise_for_status()

    return response.json()

async def main() -> None:
    async with httpx.AsyncClient() as client:
        data = await fetch_data(client)
        print(data)

if __name__ == "__main__":
    asyncio.run(main())




