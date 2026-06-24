import httpx

async def get_json(url, params = None, headers= None):
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, headers= headers)
        return response.json()
    
async def get_post(url, params = None, headers = None, payLoad = None):
    async with httpx.AsyncClient() as client:
        response = await client.post(url, params=params, headers=headers, json=payLoad)
        return response.json()
    
async def get_response(url, headers = None):
    async with httpx.AsyncClient() as client:
        return await client.get(url, headers=headers, timeout=5.0)