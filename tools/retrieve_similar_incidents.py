from typing import Dict, Any
from database.repository import query_past_incidents_from_db

def retrieve_similar_incidents(query: str) -> Dict[str, Any]:
    """
    Diagnostic Tool: Retrieves similar past incidents from Supabase memory.
    """
    past_incidents = query_past_incidents_from_db(query)

    return {
        "status": "success",
        "query": query,
        "citation": "supabase/past_incidents_table",
        "similar_incidents": past_incidents
    }
