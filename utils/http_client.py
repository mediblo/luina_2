import httpx

async def get_json(url, params = None):
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        return response.json()