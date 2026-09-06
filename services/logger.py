import json
from datetime import datetime
from config import LOGS_DIR

class StructuredLogger:
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.log_file = LOGS_DIR / f"{service_name}.log"

    def write_log(self, level: str, message: str, extra: dict = None):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "service": self.service_name,
            "level": level.upper(),
            "message": message
        }

        if extra:
            log_entry.update(extra)

        with open(self.log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    def info(self, message: str, extra: dict = None):
        self.write_log("INFO", message, extra)

    def warning(self, message: str, extra: dict = None):
        self.write_log("WARNING", message, extra)

    def error(self, message: str, extra: dict = None):
        self.write_log("ERROR", message, extra)
