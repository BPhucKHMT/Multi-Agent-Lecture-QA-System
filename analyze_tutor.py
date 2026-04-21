import re, json

# Simulate what tutor.py does in node_tutor
def parse_tutor_response(raw_content):
    """Mimic the parsing logic from tutor.py line 66-76"""
    try:
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', raw_content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_match = re.search(r'(\{.*\})', raw_content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = raw_content.strip()
        
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        return None

# Test cases
tests = {
    'fenced_json': '```json\n{"text": "hello", "video_url": []}\n```',
    'prefix_text': 'Here is response:\n{"text": "hello", "video_url": []}',
    'nested_braces': '{"text": "value {with} braces", "video_url": []}',
    'multiple_json': 'First: {"text": "hello"} Second: {"text": "world"}',
    'incomplete_brace': '{"text": "hello", "video_url": [',
    'markdown_code': '```json {"text": "hello"}```',
    'none': None,
    'empty': '',
    'plain_text': 'No JSON here',
}

print('TUTOR RESPONSE PARSING EDGE CASES')
print('=' * 80)
for name, raw in tests.items():
    if raw is None:
        print(f'{name:25} -> SKIP (None input)')
        continue
    result = parse_tutor_response(raw)
    if result:
        print(f'{name:25} -> VALID: {result}')
    else:
        print(f'{name:25} -> RETURNED_NONE / JSONDecodeError')
