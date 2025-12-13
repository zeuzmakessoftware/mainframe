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
        
        print("--- Checking Files ---")
        files = await client.list_files()
        print(f"Files: {len(files)}")
        for f in files:
            print(f"  {f.file_name} ({f.processing_status})")
            
        print("\n--- Checking Groups ---")
        groups = await client.list_groups()
        print(f"Groups: {len(groups)}")
        for g in groups:
            print(f"  {g.group_name} ({g.graph_status})")
            
        print("\nALL CHECKS PASSED")

    except Exception as e:
        print("Error encountered:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
