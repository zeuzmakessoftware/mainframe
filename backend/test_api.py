import asyncio
from graphon import app, RetrieveRequest, ExpandRequest

async def verify():
    print("Verifying /retrieve...")
    # Test Retrieve
    try:
        req = RetrieveRequest(query="test query")
        hits = await app.router.routes[-3].endpoint(req) # Assuming retrieve is 3rd from last or just call function directly?
        # Actually easier to just call the function if I can get it, but decorators wrap it.
        # Let's just import the function if possible, or use TestClient.
        from starlette.testclient import TestClient
        client = TestClient(app)
        
        response = client.post("/retrieve", json={"query": "churn story", "modalities": ["video", "text"]})
        if response.status_code == 200:
            print("✅ /retrieve success")
            data = response.json()
            print(f"   Got {len(data)} hits")
            if data:
                print(f"   Sample hit: {data[0]['node']['label']} ({data[0]['node']['type']})")
                seed_id = data[0]['node']['id']
            else:
                print("   ⚠️ No hits found (Graph might be empty). Skipping expand test with specific seed.")
                seed_id = "test-seed-id"
        else:
            print(f"❌ /retrieve failed: {response.text}")
            seed_id = None

        print("\nVerifying /expand...")
        # Test Expand
        if seed_id:
            response = client.post("/expand", json={"seed_ids": [seed_id]})
            if response.status_code == 200:
                print("✅ /expand success")
                data = response.json()
                print(f"   Nodes: {len(data['nodes'])}, Edges: {len(data['edges'])}")
                print(f"   Summary: {data['summary']}")
            else:
                 print(f"❌ /expand failed: {response.text}")
                
        print("\nVerifying /sample...")
        response = client.get("/sample")
        if response.status_code == 200:
            print("✅ /sample success")
            data = response.json()
            print(f"   Stats: {data['stats']}")
        else:
            print(f"❌ /sample failed: {response.text}")

    except Exception as e:
        print(f"❌ Verification crashed: {e}")

if __name__ == "__main__":
    asyncio.run(verify())
