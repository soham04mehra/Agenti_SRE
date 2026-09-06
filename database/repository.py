from typing import Dict, Any, List
from database.connection import get_supabase_client

# Simple local dictionary store if Supabase is disconnected
LOCAL_MEMORY_STORE: Dict[str, Any] = {}

def save_incident_state(state: Dict[str, Any]) -> bool:
    """Save the IncidentState dictionary to Supabase."""
    incident_id = state.get("incident_id")
    if not incident_id:
        return False

    client = get_supabase_client()
    if client:
        try:
            # Insert or update row in Supabase table 'incident_state'
            client.table("incident_state").upsert({
                "incident_id": incident_id,
                "raw_description": state.get("raw_description"),
                "affected_service": state.get("affected_service"),
                "symptom": state.get("symptom"),
                "confidence_score": state.get("confidence_score", 0.0),
                "status": state.get("status", "investigating"),
                "state_data": state
            }).execute()
            return True
        except Exception as err:
            print(f"⚠️ Could not save to Supabase: {err}")

    # Fallback to local dictionary
    LOCAL_MEMORY_STORE[incident_id] = state
    return True

def get_incident_state(incident_id: str) -> Dict[str, Any] | None:
    """Fetch an IncidentState dictionary by incident_id."""
    client = get_supabase_client()
    if client:
        try:
            response = client.table("incident_state").select("state_data").eq("incident_id", incident_id).execute()
            if response.data:
                return response.data[0]["state_data"]
        except Exception as err:
            print(f"⚠️ Could not fetch from Supabase: {err}")

    return LOCAL_MEMORY_STORE.get(incident_id)

def query_past_incidents_from_db(query_text: str) -> List[Dict[str, Any]]:
    """Fetch similar past incidents from Supabase table 'past_incidents'."""
    client = get_supabase_client()
    if client:
        try:
            response = client.table("past_incidents").select("past_incident_id, symptom, root_cause, resolution").limit(3).execute()
            if response.data:
                return response.data
        except Exception as err:
            print(f"⚠️ Could not fetch past incidents from Supabase: {err}")

    # Default sample past incident
    return [
        {
            "past_incident_id": "inc_past_001",
            "symptom": "Payment service DB connection timeout",
            "root_cause": "Database connection pool exhaustion due to max active connections reached.",
            "resolution": "Increased DB_POOL_MAX_CONNECTIONS limit from 10 to 30."
        }
    ]
