
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
        
        # Create a dummy file
        file_path = os.path.join(os.getcwd(), "dummy_fix_verify.txt")
        if not os.path.exists(file_path):
             with open(file_path, "w") as f:
                 f.write("Test content for fix verification")

        print(f"Uploading {file_path} with poll_until_complete=TRUE...")
        # This is the proposed fix: waiting for completion
        upload_results = await client.upload_and_process_files(
            file_paths=[file_path], 
            poll_until_complete=True
        )
        
        if not upload_results:
            print("Upload failed or returned empty.")
            return

        file_id = upload_results[0].file_id
        status = upload_results[0].processing_status
        print(f"Uploaded file ID: {file_id}, Status: {status}")
        
        if status != "SUCCESS":
            print("❌ Verification Failed: Status is not SUCCESS after polling.")
            return

        # Immediately try to create a group
        print("Attempting to create group 'verify_fix_group' immediately...")
        try:
            group_id = await client.create_group(
                file_ids=[file_id],
                group_name="verify_fix_group"
            )
            print(f"✅ Success! Group created with ID: {group_id}")
        except Exception as e:
            print("❌ Verification Failed: create_group raised exception:")
            print(e)

    except Exception as e:
        print("Outer Error:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
