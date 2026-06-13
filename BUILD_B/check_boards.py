import asyncio
import os
import sys

# Add the directory containing app to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import async_session_maker
from app.models.models import DisplayBoard
from sqlalchemy import select

async def main():
    try:
        async with async_session_maker() as db:
            res = await db.execute(select(DisplayBoard))
            boards = res.scalars().all()
            print("Found boards:")
            for b in boards:
                print(f"UUID: {b.uuid_id}, Org: {b.organization_id}, Token: {b.access_token[:10]}...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
