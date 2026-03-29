import os
import json
import logging
import hashlib
from typing import Iterator, Optional
from pydantic import ValidationError

from .task_schema import TaskObject

logger = logging.getLogger(__name__)

class TaskBankExhaustedError(Exception):
    pass

class TaskLoader:
    def __init__(self, task_bank_path: str, include_contested: bool = False):
        self.task_bank_path = task_bank_path
        self.include_contested = include_contested
        self._hash_obj = hashlib.sha256()

    @property
    def run_hash(self) -> str:
        return self._hash_obj.hexdigest()

    def load(
        self,
        focus_area: Optional[str] = None,
        difficulty: Optional[str] = None,
        limit: Optional[int] = None
    ) -> Iterator[TaskObject]:
        
        if focus_area:
            files_to_read = [f"{focus_area}_tasks.jsonl"]
        else:
            files_to_read = [
                "calib_tasks.jsonl",
                "error_detect_tasks.jsonl",
                "correction_tasks.jsonl",
                "certainty_tasks.jsonl"
            ]

        tasks_yielded = 0
        
        for filename in files_to_read:
            filepath = os.path.join(self.task_bank_path, filename)
            
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"Task bank file not found: {filepath}. Run task generation first.")

            valid_lines_in_file = 0

            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                        
                    valid_lines_in_file += 1
                    
                    try:
                        task = TaskObject.from_jsonl_line(line)
                    except json.JSONDecodeError:
                        logger.warning(json.dumps({
                            "event": "task_skipped",
                            "reason": "json_error",
                            "file": filename
                        }))
                        continue
                    except ValidationError:
                        task_id_extracted = "unknown"
                        try:
                            partial_data = json.loads(line)
                            task_id_extracted = partial_data.get("task_id", "unknown")
                        except Exception:
                            pass
                            
                        logger.warning(json.dumps({
                            "event": "task_skipped",
                            "reason": "invalid",
                            "task_id": task_id_extracted,
                            "file": filename
                        }))
                        continue

                    if getattr(task, "is_expired", False):
                        logger.info(json.dumps({
                            "event": "task_skipped",
                            "reason": "expired",
                            "task_id": task.task_id,
                            "file": filename
                        }))
                        continue
                        
                    if getattr(task, "contested", False) and not self.include_contested:
                        logger.info(json.dumps({
                            "event": "task_skipped",
                            "reason": "contested",
                            "task_id": task.task_id,
                            "file": filename
                        }))
                        continue
                        
                    # Filter by difficulty if provided
                    if difficulty and getattr(task, "difficulty", None) != difficulty:
                        continue

                    # Update run fingerprint incrementally in O(1) space
                    self._hash_obj.update(task.task_id.encode('utf-8'))
                    
                    yield task
                    tasks_yielded += 1
                    
                    if limit is not None and tasks_yielded >= limit:
                        return
            
            if valid_lines_in_file == 0:
                logger.warning(f"File {filename} is empty or has no valid lines.")
                
        if tasks_yielded == 0:
            raise TaskBankExhaustedError(
                f"No tasks passed filters: focus_area={focus_area}, "
                f"difficulty={difficulty}, include_contested={self.include_contested}"
            )
