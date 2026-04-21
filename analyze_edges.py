import re, json
from src.rag_core.agents.quiz import _extract_quiz_json_payload, QuizOutput

tests = {
    'valid': '{"quizzes": [{"question": "Q1", "options": ["A","B","C","D"], "correct_answer": "A", "explanation": "E", "video_url": "url", "timestamp": "00:00:01"}]}',
    'incomplete': '{"quizzes": [{"question": "Q1", "options": ["A","B","C","D"], "correct_answer": "A", "explanation": "E", "video_url": "url", "timestamp": "00:00:01"}',
    'empty': '{}',
    'empty_arr': '{"quizzes": []}',
    'miss_field': '{"quizzes": [{"question": "Q1"}]}',
    'wrong_type': '{"quizzes": [{"question": "Q1", "options": "ABCD", "correct_answer": "A", "explanation": "E", "video_url": "url", "timestamp": "00:00:01"}]}',
    'trailing_comma': '{"quizzes": [{"question": "Q1", "options": ["A","B","C","D"], "correct_answer": "A", "explanation": "E", "video_url": "url", "timestamp": "00:00:01"},]}',
    'none_input': None,
    'int_input': 12345,
    'array': '[{"question": "Q1"}]',
}

print('EDGE CASES FOR _extract_quiz_json_payload()')
print('=' * 80)
for name, raw in tests.items():
    try:
        result = _extract_quiz_json_payload(raw)
        if result is None:
            print(f'{name:20} -> RETURNED_NONE')
        else:
            try:
                QuizOutput.model_validate(result)
                print(f'{name:20} -> VALID ({len(result.get("quizzes", []))} quizzes)')
            except Exception as e:
                print(f'{name:20} -> PARSE_OK_BUT_INVALID: {str(e)[:45]}...')
    except Exception as e:
        print(f'{name:20} -> EXCEPTION: {str(e)[:45]}...')
