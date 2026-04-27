# INVESTIGATION DELIVERABLES INDEX

## Generated Analysis Documents

### 1. EXECUTIVE_SUMMARY.txt (208 lines)
   **Purpose**: High-level findings and root cause analysis
   **Contents**:
   - Handled model output shapes (QuizOutput, tool calls, VideoAnswer)
   - Missing/fragile shapes with examples
   - Fallback parser assessment
   - Streaming scenario root cause (HIGHEST CONFIDENCE)
   - Minimal test matrix (13 tests, 4 tiers)
   
   **Key Finding**: JsonOutputParser receives incomplete JSON during streaming
                    → No recovery mechanism exists
                    → User sees OUTPUT_PARSING_FAILURE
   
   **Read this first for: Executive overview**

### 2. JSON_PARSING_ANALYSIS.txt (267 lines)
   **Purpose**: Deep technical analysis of all parsing code
   **Contents**:
   - Section 1: Detailed handled shapes
   - Section 2: 10 unhandled edge cases with examples
   - Section 3: Fallback parser robustness assessment
   - Section 4: Streaming vulnerability breakdown
   - Section 5: Test matrix across 4 categories
   - Section 6: Root cause hypothesis with flow diagram
   
   **Read this for: Comprehensive technical documentation**

### 3. SUMMARY_TABLE.txt (98 lines)
   **Purpose**: Quick reference for status of each edge case
   **Contents**:
   - Quick pass/fail matrix for all scenarios
   - Supervisor tool parsing issues
   - Tutor parsing issues
   - Streaming root cause with flow diagram
   - Priority-ordered missing tests
   - Key files involved with line numbers
   
   **Read this for: Quick status check, key files reference**

### 4. TEST_MATRIX_CONCRETE.txt (300 lines)
   **Purpose**: Specific test cases ready to implement
   **Contents**:
   - 18 concrete test cases with inputs/expected outputs
   - Test implementation template with pytest examples
   - 6 test groups across 3 files
   - Success criteria for passing tests
   - Expected outcome after tests pass
   - 13 core regression tests (Tier 1-4)
   
   **Read this for: Implementation of regression tests**


## Key Findings Summary

### HANDLED SHAPES
✅ Plain JSON objects with all required fields
✅ Fenced JSON with ```json ...```
✅ Text-prefixed JSON
✅ Multiple tool call shape variations
✅ Unicode content

### UNHANDLED SHAPES (FRAGILE)
🔴 CRITICAL: Incomplete JSON from streaming
   - LLM generates JSON in chunks
   - Parser receives incomplete fragments
   - No recovery mechanism
   - Result: OUTPUT_PARSING_FAILURE

❌ Trailing commas in JSON
❌ Unescaped newlines in string values
❌ Multiple JSON objects in text (greedy regex)
⚠️ Type mismatches in fields (parse OK, validation fails)
⚠️ Array length mismatches (Tutor)
⚠️ Empty required arrays

### ROOT CAUSE (HIGHEST CONFIDENCE)
**Streaming scenario breaks JsonOutputParser**:
1. User generates quiz with streaming enabled
2. LLM outputs JSON incrementally via astream_events()
3. Chunks arrive incomplete: {"quizzes": [{"question"...
4. JsonOutputParser.parse() receives incomplete JSON
5. Throws JSONDecodeError
6. Fallback parser called on partial JSON
7. Fallback can't recover fragments → returns None
8. Exception re-raised → OUTPUT_PARSING_FAILURE

**Why it works for supervisor**: Uses streaming=False, gets complete response

### FILES INVOLVED
- src/rag_core/agents/quiz.py (lines 43-64, 156-163)
  - _extract_quiz_json_payload() [fallback parser]
  - node_quiz() [exception handling and recovery]

- src/rag_core/lang_graph_rag.py (lines 31-57, 79-129)
  - _normalize_tool_call_payload() [tool parsing]
  - node_supervisor() [extraction logic]

- src/rag_core/agents/tutor.py (lines 66-76)
  - JSON parsing with regex

- src/api/services/chat_service.py (lines 84-106)
  - generate_stream() [streaming entry point]

- src/generation/llm_model.py (lines 17, 35)
  - streaming=True for generation (BREAKS)
  - streaming=False for supervisor (WORKS)


## Recommendations

### IMMEDIATE (High Priority)
1. Read EXECUTIVE_SUMMARY.txt for overview
2. Review SUMMARY_TABLE.txt for quick reference
3. Implement Tier 1 tests from TEST_MATRIX_CONCRETE.txt
   - 4 streaming incomplete JSON tests
4. Add logging to _extract_quiz_json_payload() to debug failures
5. Consider streaming-aware JSON accumulator in chat_service.py

### MEDIUM PRIORITY
1. Implement Tier 2 (JSON syntax errors) tests
2. Implement Tier 3 (type validation) tests
3. Enhance fallback parser to validate extracted JSON
4. Add array length validation for Tutor responses

### NICE TO HAVE
1. Implement Tier 4 (rare cases) tests
2. Improve error messages to include "what field failed validation"
3. Consider non-streaming fallback for failing requests
4. Add metrics tracking for parsing failure types


## How to Use These Documents

### If you want to understand WHAT IS BROKEN:
→ Read SUMMARY_TABLE.txt (quick)
→ Read EXECUTIVE_SUMMARY.txt section "Streaming Scenario Root Cause"

### If you want to understand WHY it's broken:
→ Read EXECUTIVE_SUMMARY.txt (full context)
→ Read JSON_PARSING_ANALYSIS.txt section 4 & 6

### If you want to understand HOW to fix it:
→ Read TEST_MATRIX_CONCRETE.txt
→ Use implementation template at bottom for pytest tests
→ Implement Tier 1 tests first (most critical)

### If you need to debug a specific edge case:
→ Search SUMMARY_TABLE.txt for edge case name
→ Find corresponding test in TEST_MATRIX_CONCRETE.txt
→ See example input/output
→ Check JSON_PARSING_ANALYSIS.txt for technical details


## Statistics

- Total test cases identified: 18+
- Critical (Streaming) tests: 4
- High priority tests: 6
- Medium priority tests: 3
- Unhandled shapes: 10+
- Files with parsing code: 5
- Lines of parsing code analyzed: 200+
- Edge cases documented: 20+

