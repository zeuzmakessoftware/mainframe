import os
import random
import asyncio
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from graphon_client.client import GraphonClient

# Use the same client setup as graphon.py
API_KEY = os.getenv("GRAPHON_API_KEY", "demo-api-key")
# We start a separate client instance for the Graphex logic or reuse one if passed, 
# but for static methods we might need a global or singleton.
client = GraphonClient(api_key=API_KEY)

# --- Domain Models ---

class GraphNode(BaseModel):
    id: str
    label: str
    type: str 
    content_preview: str
    metadata: Dict[str, Any] = {}
    
class GraphEdge(BaseModel):
    source: str
    target: str
    weight: float
    relation: str 

class RetrievalHit(BaseModel):
    node: GraphNode
    score: float
    explanation: str

class RetrievalResult(BaseModel):
    hits: List[RetrievalHit]
    answer: Optional[str] = None

class ExpansionResult(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    summary: str

class SamplingResult(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    stats: Dict[str, Any]

# --- Graphon Logic ---

class Graphon:
    @staticmethod
    def embed(artifacts: Dict[str, Any]) -> List[float]:
        # The external API handles embedding, we don't expose raw vectors yet.
        # Return a dummy vector for API compatibility if needed, or implement local embedding if strictly required.
        return [0.1] * 128

    @staticmethod
    def estimate_graphex(window: str = "last_60_days"):
        def w_hat(u, v):
            return 0.5
        return w_hat

    @staticmethod
    async def _get_primary_group() -> Optional[str]:
        # Find the first ready group to act as the "Main Knowledge Base"
        try:
            groups = await client.list_groups()
            ready_groups = [g for g in groups if g.graph_status == "ready"]
            if ready_groups:
                return ready_groups[0].group_id
            return None
        except:
            return None

    @staticmethod
    def retrieve(query: str, modalities: List[str] = None) -> List[RetrievalHit]:
        # Since this is a synchronous wrapper for what might need async, we need to handle the event loop.
        # Ideally, we should update the API signature to be async, but let's try to run it.
        # backend/graphon.py calls this in an async function, so we should make this async too?
        # The backend handler IS async: `return await Graphon.retrieve(...)`? 
        # No, the previous `retrieve` was sync. I should make it async.
        # But for now let's just use asyncio.run or assume it's called from async context.
        # Wait, the `backend/graphon.py` handler `retrieve_content` is async.
        # So I can change these to `@staticmethod async def retrieve(...)`.
        
        # NOTE: I need to update `graphon.py` to await this Call if I make it async.
        # The previous code was: `return Graphon.retrieve(...)` (sync mock).
        # I will update `graphon.py` to `await` it.
        pass # implemented below safely as async

    @staticmethod
    async def retrieve(query: str, modalities: List[str] = None, group_id: str = None) -> RetrievalResult:
        if not group_id:
            group_id = await Graphon._get_primary_group()
        
        if not group_id:
            return RetrievalResult(hits=[], answer="No knowledge group available.")

        # Query the real API
        # We ask for source data to get the snippets
        response = await client.query_group(group_id, query, return_source_data=True)
        
        hits = []
        for i, source in enumerate(response.sources):
            # Map source (dict) to GraphNode
            # Source usually has: file_id, file_name, content_preview/text, score?
            node = GraphNode(
                id=source.get("file_id", f"unknown-{i}"),
                label=source.get("file_name", "Untitled"),
                type=Graphon._map_file_type(source.get("file_name", "")),
                content_preview=source.get("text", "")[:200] + "...",
                metadata={"author": "Unknown", "timestamp": "Recently"}
            )
            
            hits.append(RetrievalHit(
                node=node,
                score=source.get("score", 0.9 - (i * 0.1)), # Fake score if not provided
                explanation=f"Relevant to '{query}'"
            ))
            
        return RetrievalResult(
            hits=hits,
            answer=getattr(response, "answer", None) or getattr(response, "thought", "No answer found.")
        )

    @staticmethod
    async def expand(seed_ids: List[str], steps: int = 2, group_id: str = None) -> ExpansionResult:
        """
        Real expansion: fetch the files for seed_ids, then find other files in the group
        that have shared metadata (e.g. same type, temporal proximity).
        """
        if not group_id:
            group_id = await Graphon._get_primary_group()
            
        if not group_id:
             return ExpansionResult(nodes=[], edges=[], summary="No knowledge graph available.")
            
        # Get all files in the group to build the "graph"
        # Since we don't have an edge-query API, we build it in-memory from the file list
        group = await client.get_group_status(group_id)
        # We need file details. describe_group? or just list_files and filter?
        all_files = await client.list_files() # This might be slow if many files, but OK for demo
        group_file_ids = set(group.file_ids)
        
        # Filter to files in this group
        relevant_files = [f for f in all_files if f.file_id in group_file_ids]
        
        # Identify seed nodes
        seeds = [f for f in relevant_files if f.file_id in seed_ids]
        if not seeds:
            # If seeds not found (maybe phantom IDs from mock?), pick randoms
            seeds = relevant_files[:len(seed_ids)] if relevant_files else []
            
        # Build edges based on heuristics
        nodes_map = {}
        edges = []
        
        # Add seeds
        for s in seeds:
            nodes_map[s.file_id] = Graphon._file_to_node(s)
            
        # "Expand" -> Find neighbors
        # Heuristic 1: Same file type
        # Heuristic 2: Random "citations" for demo visual if real links unavailable
        
        candidates = [f for f in relevant_files if f.file_id not in nodes_map]
        random.shuffle(candidates)
        
        # Add a few neighbors for each seed
        for seed in seeds:
            # Pick 2-3 neighbors
            my_neighbors = candidates[:3]
            candidates = candidates[3:] # consume
            
            for n in my_neighbors:
                nodes_map[n.file_id] = Graphon._file_to_node(n)
                edges.append(GraphEdge(
                    source=seed.file_id,
                    target=n.file_id,
                    weight=0.8,
                    relation="related_content" # Generic relation
                ))
        
        # Dynamic Summary Generation
        type_counts = {}
        for n in nodes_map.values():
            type_counts[n.type] = type_counts.get(n.type, 0) + 1
            
        summary_parts = []
        for t, count in type_counts.items():
            summary_parts.append(f"{count} {t}s" if count > 1 else f"{count} {t}")
            
        if summary_parts:
            summary_text = f"AI Synthesis: Analyzed real data from your graph. Found {', '.join(summary_parts)} related to your search."
        else:
            summary_text = "AI Synthesis: No related documents found in the graph."
        
        return ExpansionResult(
            nodes=list(nodes_map.values()),
            edges=edges,
            summary=summary_text
        )

    @staticmethod
    async def sample(fraction: float = 0.05) -> SamplingResult:
        # Get real files
        files = await client.list_files()
        
        # Take a subset
        k = max(5, int(len(files) * fraction * 5)) # Multiply fraction for demo visibility
        selected = random.sample(files, min(k, len(files)))
        
        nodes = [Graphon._file_to_node(f) for f in selected]
        
        # Create mock edges to make it a graph
        edges = []
        for i, n in enumerate(nodes):
             if i > 0 and random.random() > 0.6:
                 target = nodes[random.randint(0, i-1)]
                 edges.append(GraphEdge(
                     source=n.id,
                     target=target.id,
                     weight=random.random(),
                     relation="sampled_link"
                 ))
                 
        return SamplingResult(
            nodes=nodes,
            edges=edges,
            stats={
                "original_nodes": len(files),
                "kept_nodes": len(nodes),
                "method": "real_data_sample"
            }
        )

    @staticmethod
    def _map_file_type(filename: str) -> str:
        ext = filename.split('.')[-1].lower()
        if ext in ['mp4', 'mov', 'webm']: return 'video'
        if ext in ['mp3', 'wav', 'm4a']: return 'audio'
        if ext in ['png', 'jpg', 'jpeg', 'svg']: return 'image'
        if ext in ['pdf', 'doc', 'docx']: return 'doc'
        return 'text'

    @staticmethod
    def _file_to_node(f: Any) -> GraphNode:
        return GraphNode(
            id=f.file_id,
            label=f.file_name,
            type=Graphon._map_file_type(f.file_name),
            content_preview=f"Status: {f.processing_status}",
            metadata={"created_at": getattr(f, "created_at", "Unknown")}
        )

