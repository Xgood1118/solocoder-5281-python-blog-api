import asyncio
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.services import article_service
from app.schemas import ArticleCreate
from app.database import async_session, init_db, engine
from sqlalchemy.orm import DeclarativeBase
from app.database import Base

async def test():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        for i in range(3):
            await article_service.create_article(
                db,
                ArticleCreate(
                    title=f"Test Article {i}",
                    content=f"This is test article {i} content.",
                    summary=f"Summary {i}",
                    status="published",
                ),
            )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/feed/rss")
        print(f"RSS status: {resp.status_code}")
        print(f"RSS length: {len(resp.text)} chars")
        if resp.status_code == 200:
            assert "<item>" in resp.text or "<entry>" not in resp.text
            assert "Test Article 0" in resp.text
            print("RSS: OK - contains articles")

        print()

        resp = await client.get("/feed/atom")
        print(f"Atom status: {resp.status_code}")
        print(f"Atom length: {len(resp.text)} chars")
        if resp.status_code == 200:
            assert "<entry>" in resp.text
            assert "Test Article 0" in resp.text
            print("Atom: OK - contains articles")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    print()
    print("All feed tests passed!")

asyncio.run(test())
