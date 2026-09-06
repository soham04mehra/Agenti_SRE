from tools.fetch_logs import fetch_logs
from tools.query_metrics import query_metrics
from tools.get_deployments import get_deployments
from tools.search_codebase import search_codebase
from tools.retrieve_similar_incidents import retrieve_similar_incidents

# Tool Phonebook: Maps string tool names to executable Python functions
TOOL_REGISTRY = {
    "fetch_logs": fetch_logs,
    "query_metrics": query_metrics,
    "get_deployments": get_deployments,
    "search_codebase": search_codebase,
    "retrieve_similar_incidents": retrieve_similar_incidents
}

def execute_tool_by_name(tool_name: str, **kwargs) -> dict:
    """
    Dispatcher function: Executes a diagnostic tool by its string name.
    """
    tool_func = TOOL_REGISTRY.get(tool_name)
    
    if not tool_func:
        return {
            "status": "error",
            "message": f"Unknown tool name '{tool_name}'"
        }
    
    # Run the function and return its result dictionary
    return tool_func(**kwargs)
