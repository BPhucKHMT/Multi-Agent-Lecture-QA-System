"""
Simulate streaming scenario where JSON is sent incrementally
This happens in chat_service.py with astream_events
"""

def simulate_streaming_json():
    """Simulate partial JSON fragments coming in via streaming"""
    chunks = [
        '{"quizzes": [',
        '{"question": "What is CNN?", "options": ["A","B","C","D"], ',
        '"correct_answer": "A", "explanation": "explanation text", ',
        '"video_url": "https://youtube.com/watch?v=abc", "timestamp": "00:00:01"}',
        ']}',
    ]
    
    partial = ""
    for i, chunk in enumerate(chunks):
        partial += chunk
        print(f"Chunk {i}: partial='{partial[:60]}...'")
        # Try to parse at each step
        try:
            import json
            obj = json.loads(partial)
            print(f"  -> PARSED OK")
        except json.JSONDecodeError as e:
            print(f"  -> JSON ERROR: {str(e)[:50]}")

print('STREAMING JSON ACCUMULATION SCENARIO')
print('=' * 80)
simulate_streaming_json()

# Edge case: What if streaming gives us this?
print('\n\nEDGE CASE: Streaming with text before JSON')
print('=' * 80)
streaming_with_text = [
    'Here is your quiz:',
    ' ```json',
    ' {"quizzes": [{"question": "Q1", ',
    '"options": ["A","B","C","D"], "correct_answer": "A", ',
    '"explanation": "E", "video_url": "url", "timestamp": "00:00:01"}]}',
    '```',
]
partial = ""
for i, chunk in enumerate(streaming_with_text):
    partial += chunk
    print(f"Chunk {i}: partial='{partial[-40:] if len(partial) > 40 else partial}'")
