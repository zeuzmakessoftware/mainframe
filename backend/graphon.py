from dotenv import load_dotenv
load_dotenv()

from typing import List, Optional
import os
import shutil
import tempfile

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from graphon_client.client import GraphonClient, FileDetail, GroupDetail, GroupListItem, QueryResponse
from graphon_client.client import GraphonClient, FileDetail, GroupDetail, GroupListItem, QueryResponse
from graphex import Graphon, RetrievalHit, ExpansionResult, SamplingResult, GraphNode, RetrievalResult

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

class RetrieveRequest(BaseModel):
    query: str
    modalities: List[str] = ["video", "audio", "text", "ticket"]
    group_id: Optional[str] = None

class ExpandRequest(BaseModel):
    seed_ids: List[str]
    steps: int = 2
    group_id: Optional[str] = None

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
async def upload_file(files: List[UploadFile] = File(...)):
    """
    Upload and process multiple files.
    This handles the full flow:
    1. Save all to temp
    2. Trigger batch processing
    """
    try:
        # Create a temp directory to save the files
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_file_paths = []
            
            # Save all files to temp
            for file in files:
                tmp_path = os.path.join(tmp_dir, file.filename)
                with open(tmp_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                temp_file_paths.append(tmp_path)

            try:
                # Upload and process all files in one go
                results = await client.upload_and_process_files(
                    file_paths=temp_file_paths, 
                    poll_until_complete=True # Wait for processing to ensure files are ready for grouping
                )
                
                if not results:
                     # If no results, something might be wrong, but with empty list it shouldn't happen if inputs exist
                     # If we sent files but got nothing, maybe partial fail?
                     # Let's just return what we got
                     pass 
                
                # Return the list of file details
                return results

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

@app.post("/retrieve", response_model=RetrievalResult)
async def retrieve_content(request: RetrieveRequest):
    """Retrieve multimodal content based on query."""
    try:
        return await Graphon.retrieve(request.query, request.modalities, request.group_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/expand", response_model=ExpansionResult)
async def expand_graph(request: ExpandRequest):
    """Expand the graph from seed nodes."""
    try:
        return await Graphon.expand(request.seed_ids, request.steps, request.group_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sample", response_model=SamplingResult)
async def sample_graph():
    """Sample a sparse subgraph for training/eval."""
    try:
        return await Graphon.sample()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# Supabase / Trails Endpoints
# ============================================================================

from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Optional[Client] = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Warning: Failed to initialize Supabase client: {e}")

class Trail(BaseModel):
    id: str
    query: str
    created_at: str
    synthesis: Optional[str] = None
    nodes: Optional[List[dict]] = None
    edges: Optional[List[dict]] = None

class CreateTrailRequest(BaseModel):
    query: str
    synthesis: Optional[str] = None
    nodes: Optional[List[dict]] = None
    edges: Optional[List[dict]] = None

@app.get("/trails", response_model=List[Trail])
async def get_trails():
    """Get recent trails from Supabase."""
    if not supabase:
        # Fallback if unconfigured
        return []
    try:
        response = supabase.table("trails").select("*").order("created_at", desc=True).limit(20).execute()
        return response.data
    except Exception as e:
        print(f"Error fetching trails: {e}")
        return [] # Return empty on error to avoid breaking UI

@app.post("/trails")
async def create_trail(request: CreateTrailRequest):
    """Save a new trail."""
    if not supabase:
        return {"status": "skipped", "reason": "supabase_not_configured"}
    try:
        # Check if exists to avoid dupes (optional, but good for UX)
        # For now just insert
        data = {
            "query": request.query,
            "synthesis": request.synthesis,
            "nodes": request.nodes,
            "edges": request.edges
        }
        response = supabase.table("trails").insert(data).execute()
        return response.data
    except Exception as e:
        print(f"Error creating trail: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/trails/{trail_id}")
async def delete_trail(trail_id: str):
    """Delete a trail."""
    if not supabase:
         return {"status": "skipped"}
    try:
        supabase.table("trails").delete().eq("id", trail_id).execute()
        return {"status": "success"}
    except Exception as e:
        print(f"Error deleting trail: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)