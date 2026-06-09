import asyncio
from httpx import ASGITransport, AsyncClient
from app.main import app

async def test():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/feed/rss")
        print(f"RSS status: {resp.status_code}")
        if resp.status_code == 200:
            print(f"RSS content length: {len(resp.text)} chars")
            print("--- RSS first 400 chars ---")
            print(resp.text[:400])
            print("...")
        else:
            print(f"Error: {resp.text[:300]}")

        print()

        resp = await client.get("/feed/atom")
        print(f"Atom status: {resp.status_code}")
        if resp.status_code == 200:
            print(f"Atom content length: {len(resp.text)} chars")
            print("--- Atom first 400 chars ---")
            print(resp.text[:400])
            print("...")
        else:
            print(f"Error: {resp.text[:300]}")

        print()
        print("Testing /feed alias:")
        resp = await client.get("/feed")
        print(f"/feed status: {resp.status_code}")

asyncio.run(test())
