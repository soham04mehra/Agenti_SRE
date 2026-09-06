from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent

def search_codebase(query: str, service_name: str = "payment_service") -> dict:
    """
    Diagnostic Tool: Searches service source code for relevant configuration
    or implementation patterns (DB pool limits, timeout configs, memory).
    """
    services_dir = BASE_DIR / "services"
    matching_snippets = []

    if services_dir.exists():
        for file_path in services_dir.glob("*.py"):
            with open(file_path, "r") as f:
                lines = f.readlines()
                for line_idx, line in enumerate(lines, 1):
                    if query.lower() in line.lower():
                        matching_snippets.append({
                            "file": str(file_path.name),
                            "line_number": line_idx,
                            "code_snippet": line.strip()
                        })

    return {
        "status": "success",
        "query": query,
        "service": service_name,
        "matches_found": len(matching_snippets),
        "results": matching_snippets[:5]
    }
