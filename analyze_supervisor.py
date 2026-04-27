import json
from src.rag_core.lang_graph_rag import _normalize_tool_call_payload

# Test all variations
tests = {
    'tool_calls_array': '{"tool_calls": [{"name": "GenerateQuiz", "args": {"topic": "CNN"}}]}',
    'single_tool_call': '{"tool_call": {"name": "GenerateQuiz", "args": {"topic": "CNN"}}}',
    'tool_args': '{"tool": "GenerateQuiz", "args": {"topic": "CNN"}}',
    'tool_arguments': '{"tool": "GenerateQuiz", "arguments": {"topic": "CNN"}}',
    'name_args': '{"name": "GenerateQuiz", "args": {"topic": "CNN"}}',
    'name_arguments': '{"name": "GenerateQuiz", "arguments": {"topic": "CNN"}}',
    'missing_name': '{"args": {"topic": "CNN"}}',
    'empty_args': '{"name": "GenerateQuiz", "args": {}}',
    'args_not_dict': '{"name": "GenerateQuiz", "args": "not_a_dict"}',
    'empty_object': '{}',
}

print('SUPERVISOR TOOL PARSING EDGE CASES')
print('=' * 80)
for name, raw in tests.items():
    try:
        parsed = json.loads(raw)
        result = _normalize_tool_call_payload(parsed)
        if result:
            print(f'{name:25} -> VALID: {result[0].get("name", "?")} (args keys: {list(result[0].get("args", {}).keys())})')
        else:
            print(f'{name:25} -> RETURNED_NONE')
    except Exception as e:
        print(f'{name:25} -> EXCEPTION: {str(e)[:45]}...')
