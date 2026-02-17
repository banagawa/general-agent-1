from datetime import datetime

def log_event(event: str):
    timestamp = datetime.utcnow().isoformat()
    print(f"[AUDIT]{timestamp} -  {event}")
