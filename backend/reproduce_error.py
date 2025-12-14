
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
        
        # Create a dummy file if not exists (though I just created it)
        file_path = os.path.join(os.getcwd(), "dummy.txt")
        if not os.path.exists(file_path):
             with open(file_path, "w") as f:
                 f.write("Test content")

        print(f"Uploading {file_path} with poll_until_complete=False...")
        upload_results = await client.upload_and_process_files(
            file_paths=[file_path], 
            poll_until_complete=False
        )
        
        if not upload_results:
            print("Upload failed or returned empty.")
            return

        file_id = upload_results[0].file_id # Accessing attribute assuming FileObject
        print(f"Uploaded file ID: {file_id}")
        
        # Immediately try to create a group
        print("Attempting to create group 'repro_race_condition' immediately...")
        try:
            group_id = await client.create_group(
                file_ids=[file_id],
                group_name="repro_race_condition"
            )
            print(f"Unexpected Success! Group created with ID: {group_id}")
        except Exception as e:
            print("Caught expected error during create_group:")
            print(e)
            # import traceback
            # traceback.print_exc()

    except Exception as e:
        print("Outer Error:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
