import json
from typing import Dict, Any, Optional
from pydantic import BaseModel

class TaskObject(BaseModel):
    """Schema representing a single metacognitive evaluation task."""
    task_id: str
    focus_area: str
    prompt: str
    ground_truth: str
    metadata: Dict[str, Any] = {}

    @classmethod
    def from_jsonl_line(cls, line: str) -> "TaskObject":
        data = json.loads(line)
        return cls(**data)
        
    @property
    def is_expired(self) -> bool:
        return self.metadata.get("is_expired", False)
        
    @property
    def contested(self) -> bool:
        return self.metadata.get("contested", False)
        
    @property
    def difficulty(self) -> Optional[str]:
        return self.metadata.get("difficulty")
