import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# Load dotenv to get API keys
from dotenv import load_dotenv
load_dotenv(dotenv_path=ROOT / ".env")

from experiments.src.data.chunk_loader import load_chunks
from src.generation.llm_model import get_internal_llm
from langchain_core.messages import HumanMessage, SystemMessage

# Courses details
COURSE_MAP = {
    "CS114": "Machine Learning (Học máy)",
    "CS116": "Lập trình Python cho Máy học",
    "CS315": "Máy học nâng cao",
    "CS431": "Các kỹ thuật học sâu và ứng dụng"
}

ADMIN_PATTERNS = [
    r"\bđại học quốc gia\b",
    r"\bvietnam national university\b",
    r"\btrường đại học công nghệ\b",
    r"\bkhoa khoa học máy tính\b",
    r"\bkhoa kỹ thuật máy tính\b",
    r"\bgiảng viên\b",
    r"\bTS\.\s+[A-ZÀ-Ỹ]",
    r"\bThS\.\s+[A-ZÀ-Ỹ]",
    r"\bph\.d\b",
    r"\btiến sĩ\b",
    r"\bthạc sĩ\b",
    r"\bđhqg-hcm\b",
    r"\bvnu-hcm\b"
]

def is_boilerplate(content: str) -> bool:
    content_clean = content.strip()
    if len(content_clean) < 100:
        return True
        
    lines = content_clean.split('\n')
    remaining_lines = []
    for line in lines:
        if any(re.search(pat, line, re.IGNORECASE if "TS." not in pat and "ThS." not in pat else 0) for pat in ADMIN_PATTERNS):
            continue
        remaining_lines.append(line)
        
    remaining_text = "\n".join(remaining_lines).strip()
    if len(remaining_text) < 80:
        return True
        
    return False

def normalize_text(text: str) -> str:
    text = text.lower().strip()
    # remove punctuation and standard marks
    text = re.sub(r'[^\w\s]', '', text)
    return " ".join(text.split())

def parse_json_list(text: str) -> list[str]:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```json") or lines[0].startswith("```"):
            lines = lines[1:]
        if lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return [str(item).strip() for item in data]
    except Exception:
        match = re.search(r"\[\s*\".*\"\s*\]", text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                if isinstance(data, list):
                    return [str(item).strip() for item in data]
            except Exception:
                pass
    
    # Fallback parsing
    queries = []
    for line in text.split("\n"):
        line = re.sub(r"^\d+[\.\-\s]+", "", line.strip()).strip("\"' ")
        if line:
            queries.append(line)
    return queries

def call_openai_with_retry(llm, messages, max_retries=5):
    delay = 1.0
    for attempt in range(max_retries):
        try:
            response = llm.invoke(messages)
            return response.content
        except Exception as e:
            print(f"Error calling OpenAI API (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                raise e
            time.sleep(delay)
            delay *= 2

def main():
    import argparse
    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed

    parser = argparse.ArgumentParser(description="Generate synthetic training queries using GPT-4o-mini.")
    parser.add_argument("--limit", type=int, default=None, help="Limit the number of chunks to process.")
    parser.add_argument("--workers", type=int, default=1, help="Number of concurrent workers (default: 1).")
    args = parser.parse_args()

    output_dir = ROOT / "experiments/data/finetune"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "synthetic_queries.jsonl"
    
    # 1. Load ground truth pilot queries to prevent leakage
    eval_queries = set()
    gt_path = ROOT / "experiments/data/ground_truth/ground_truth_pilot.jsonl"
    if gt_path.exists():
        with open(gt_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    record = json.loads(line)
                    if "question" in record:
                        eval_queries.add(normalize_text(record["question"]))
        print(f"Loaded {len(eval_queries)} evaluation queries to prevent leakage.")
    else:
        print("Warning: ground_truth_pilot.jsonl not found! Make sure you run from root or check path.")
        
    # 2. Check already generated queries to resume
    processed_doc_ids = set()
    generated_count = 0
    if output_file.exists():
        with open(output_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    record = json.loads(line)
                    processed_doc_ids.add(record.get("pos_doc_id"))
                    generated_count += 1
        print(f"Resuming progress. Already processed {len(processed_doc_ids)} chunks, found {generated_count} synthetic queries.")
        
    # 3. Load all recursive chunks
    chunks_dir = ROOT / "experiments/data/chunks/recursive"
    all_chunks = load_chunks(chunks_dir, strategy_id="recursive")
    print(f"Loaded {len(all_chunks)} recursive chunks.")
    
    # 4. Filter chunks and identify unprocessed ones
    chunks_to_process = []
    for chunk in all_chunks:
        doc_id = chunk["doc_id"]
        if doc_id in processed_doc_ids:
            continue
        if is_boilerplate(chunk["text"]):
            continue
        chunks_to_process.append(chunk)
        
    print(f"Total chunks to process: {len(chunks_to_process)}")
    if args.limit is not None:
        chunks_to_process = chunks_to_process[:args.limit]
        print(f"Limiting to first {len(chunks_to_process)} chunks.")
        
    if not chunks_to_process:
        print("No new chunks to process. All done.")
        return

    # Initialize LLM
    llm = get_internal_llm()
    
    system_prompt = (
        "Bạn là một sinh viên đang học tập các môn chuyên ngành Khoa học Máy tính / Công nghệ Thông tin tại trường Đại học Công nghệ Thông tin.\n"
        "Hãy đóng vai sinh viên thông thái để đặt câu hỏi thảo luận, hỏi đáp thực tế từ các slide bài giảng."
    )
    
    write_lock = threading.Lock()

    def process_chunk(idx, chunk):
        doc_id = chunk["doc_id"]
        text = chunk["text"]
        course_id = chunk["metadata"].get("course_id", "CS")
        course_name = COURSE_MAP.get(course_id, "Khoa học Máy tính")
        
        prompt = (
            f"Bạn đang ôn tập môn học: {course_name}.\n"
            f"Hãy đọc kỹ slide bài giảng sau đây:\n"
            f"---\n"
            f"{text}\n"
            f"---\n"
            f"Hãy viết ra chính xác 3 câu hỏi ngắn gọn, tự nhiên, phong phú mà một sinh viên có thể hỏi dựa trên slide này.\n"
            f"Yêu cầu:\n"
            f"1. Câu hỏi ngắn gọn (dưới 20 từ), tập trung vào các khái niệm, cơ chế, công thức hoặc mã nguồn được đề cập.\n"
            f"2. Sử dụng thuật ngữ tiếng Anh đan xen (code-switching) giống cách sinh viên IT Việt Nam dùng (ví dụ: 'train model', 'loss function', 'overfitting', 'gom cụm', 'giảm chiều').\n"
            f"3. Câu hỏi phải trả lời được trực tiếp và đầy đủ dựa vào slide trên.\n"
            f"4. Trả về dưới dạng một danh sách chuỗi JSON (JSON list of strings). Ví dụ: [\"câu hỏi 1\", \"câu hỏi 2\", \"câu hỏi 3\"]"
        )
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=prompt)
        ]
        
        print(f"[{idx+1}/{len(chunks_to_process)}] Generating queries for {doc_id} ({course_id})...")
        try:
            response_text = call_openai_with_retry(llm, messages)
            queries = parse_json_list(response_text)
            
            # Check format and count
            if len(queries) != 3:
                # Try once more with simpler prompt
                retry_messages = messages + [HumanMessage(content="Hãy trả về đúng cấu trúc JSON list of strings chứa chính xác 3 câu hỏi.")]
                response_text = call_openai_with_retry(llm, retry_messages)
                queries = parse_json_list(response_text)
            
            valid_queries = []
            for q in queries:
                norm_q = normalize_text(q)
                # Skip if too short or matches any query in test set
                if len(norm_q) < 10:
                    continue
                if norm_q in eval_queries:
                    print(f"Skipping query matching test set to prevent leakage: {q}")
                    continue
                valid_queries.append(q)
            
            if valid_queries:
                with write_lock:
                    with open(output_file, "a", encoding="utf-8") as out_f:
                        for q in valid_queries:
                            record = {
                                "query": q,
                                "pos_doc_id": doc_id,
                                "pos_doc_content": text,
                                "course": course_id,
                                "metadata": {
                                    "video_url": chunk["metadata"].get("video_url"),
                                    "filename": chunk["metadata"].get("filename"),
                                    "start_timestamp": chunk["metadata"].get("start_timestamp"),
                                    "end_timestamp": chunk["metadata"].get("end_timestamp")
                                }
                            }
                            out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                        out_f.flush()
        except Exception as e:
            print(f"Error processing chunk {doc_id}: {e}")

    if args.workers > 1:
        print(f"Starting query generation using ThreadPoolExecutor with {args.workers} workers...")
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(process_chunk, idx, chunk): chunk for idx, chunk in enumerate(chunks_to_process)}
            for future in as_completed(futures):
                pass
    else:
        print("Starting query generation sequentially...")
        for idx, chunk in enumerate(chunks_to_process):
            process_chunk(idx, chunk)
            time.sleep(0.1)

    print("Generation completed successfully.")

if __name__ == "__main__":
    main()
