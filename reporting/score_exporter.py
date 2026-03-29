# e:/kaggle hackathon google/metacognition-benchmark/reporting/score_exporter.py
"""
Utilities to export evaluation results to JSON and CSV formats.
"""
import json
import csv
from typing import List, Dict, Any
import os

class ScoreExporter:
    """Handles exporting MetaCog results to various formats."""
    
    @staticmethod
    def export_json(results: List[Dict[str, Any]], filepath: str):
        """Exports results to a JSON file."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=4)
            
    @staticmethod
    def export_csv(results: List[Dict[str, Any]], filepath: str):
        """Exports flat results to a CSV file."""
        if not results:
            return
            
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        keys = results[0].keys()
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            dict_writer = csv.DictWriter(f, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(results)
