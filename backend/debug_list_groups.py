import asyncio
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.getcwd())

from graphon_client.client import GraphonClient

load_dotenv()

API_KEY = os.getenv("GRAPHON_API_KEY")

async def main():
    try:
        client = GraphonClient(api_key=API_KEY)
        print("Calling list_groups()...")
        groups = await client.list_groups()
        print(f"Success! Found {len(groups)} groups.")
        for g in groups:
            print(f" - {g.group_name} ({g.graph_status})")
            
    except Exception as e:
        print("Error encountered:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
