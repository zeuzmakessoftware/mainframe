import os
import shutil
import tempfile
from typing import List, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from graphon_client.client import GraphonClient, FileDetail, GroupDetail, GroupListItem, QueryResponse

load_dotenv()

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Client
# In a real app, API key should come from environment variables
API_KEY = os.getenv("GRAPHON_API_KEY", "demo-api-key")
# Use localhost for now as per client.py default for testing, or the real one if env var set
BASE_URL = os.getenv("GRAPHON_API_URL", "http://localhost:8081") # Defaulting to local as per request context implication or client default
# Actually client.py defaults to prod URL, let's respect that unless override.
# But wait, the user prompt implies "dashboard that works as a frontend with all of the functions in client.py"
# The client.py has a hardcoded prod URL but also a commented out localhost.
# I will initialize it without base_url to use the default in client.py, which seems to be the production one:
# "https://api-frontend-485250924682.us-central1.run.app"
# I should probably allow it to be configurable.

client = GraphonClient(api_key=API_KEY)

# ============================================================================
# Pydantic Models for Request Bodies
# ============================================================================

class GroupCreateRequest(BaseModel):
    group_name: str
    file_ids: List[str]

class QueryRequest(BaseModel):
    query: str
    return_source_data: bool = False

# ============================================================================
# Endpoints
# ============================================================================

@app.get("/files", response_model=List[FileDetail])
async def list_files():
    """List all files."""
    try:
        return await client.list_files()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/files/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload and process a file.
    This handles the full flow:
    1. Save to temp
    2. Get signed URL
    3. Upload to GCS
    4. Trigger processing
    """
    try:
        # Create a temp directory to save the file with its original name
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = os.path.join(tmp_dir, file.filename)
            
            with open(tmp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            try:
                # Determine file type locally or let client do it
                # Client's upload_and_process_files handles the whole flow
                # We want to wait for it to be processed? simpler for now to say yes or return "PROCESSING"
                # client.upload_and_process_files returns a list of FileObjects
                
                results = await client.upload_and_process_files(
                    file_paths=[tmp_path], 
                    poll_until_complete=False # Return immediately with PROCESSING status
                )
                
                if not results:
                     raise HTTPException(status_code=400, detail="Upload failed")
                
                return results[0]

            except Exception as inner_e:
                raise inner_e
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/groups", response_model=List[GroupListItem])
async def list_groups():
    """List all groups."""
    try:
        # Note: client.list_groups returns List[GroupListItem]
        return await client.list_groups() 
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/groups")
async def create_group(request: GroupCreateRequest):
    """Create a new group."""
    try:
        group_id = await client.create_group(
            file_ids=request.file_ids,
            group_name=request.group_name
        )
        return {"group_id": group_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/groups/{group_id}", response_model=GroupDetail)
async def get_group(group_id: str):
    """Get group details."""
    try:
        return await client.get_group_status(group_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/groups/{group_id}/query", response_model=QueryResponse)
async def query_group(group_id: str, request: QueryRequest):
    """Query a group."""
    try:
        return await client.query_group(
            group_id=group_id,
            query=request.query,
            return_source_data=request.return_source_data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)