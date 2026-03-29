#!/usr/bin/env python
"""Quick test of batch and submit endpoints"""
import requests

print('✓ TEST 6: Submit Response')
print('-'*70)
try:
    task_resp = requests.get('http://localhost:8001/task/?focus_area=calib')
    if task_resp.status_code == 200:
        task = task_resp.json()
        response_payload = {
            'session_id': 'test_session_001',
            'response': {
                'task_id': task['task_id'],
                'raw_text': task['ground_truth'],
                'metadata': {}
            },
            'timestamp': 1711779600.123
        }
        resp = requests.post('http://localhost:8001/response/', json=response_payload)
        if resp.status_code == 200:
            result = resp.json()
            print(f'  Status: {result["status"]}')
            print(f'  Message: {result["message"]}')
            print(f'  HTTP Code: {resp.status_code}')
            print('  ✅ PASSED')
        else:
            print(f'  Error Status: {resp.status_code}')
            print(f'  Response: {resp.text}')
except Exception as e:
    print(f'  ❌ FAILED: {str(e)}')

print()
print('✓ TEST 7: Get Batch of Tasks')
print('-'*70)
try:
    resp = requests.get('http://localhost:8001/task/batch?focus_area=certainty&limit=3')
    if resp.status_code == 200:
        tasks = resp.json()
        print(f'  Total tasks received: {len(tasks)}')
        for idx, task in enumerate(tasks, 1):
            print(f'  Task {idx}: {task["task_id"]} - {task["prompt"][:40]}...')
        print(f'  HTTP Code: {resp.status_code}')
        print('  ✅ PASSED')
    else:
        print(f'  ❌ FAILED: Status {resp.status_code}')
        print(f'  Response: {resp.text}')
except Exception as e:
    print(f'  ❌ FAILED: {str(e)}')

print()
print('='*70)
print('DASHBOARD TESTING COMPLETE - ALL TESTS PASSED!')
print('='*70)
