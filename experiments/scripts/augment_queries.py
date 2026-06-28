import json
import os
import sys
import time
import argparse
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# Load dotenv to get API keys
from dotenv import load_dotenv
load_dotenv(dotenv_path=ROOT / ".env")

from src.generation.llm_model import get_internal_llm
from langchain_core.messages import HumanMessage, SystemMessage

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
        pass
    
    # Fallback line-by-line parsing
    import re
    queries = []
    for line in text.split("\n"):
        line = re.sub(r"^\d+[\.\-\s]+", "", line.strip()).strip("\"' ")
        if line:
            queries.append(line)
    return queries

def main():
    parser = argparse.ArgumentParser(description="Paraphrase and augment synthetic queries using GPT-4o-mini.")
    parser.add_argument("--batch-size", type=int, default=15, help="Number of queries to paraphrase per API call.")
    parser.add_argument("--workers", type=int, default=4, help="Number of concurrent threads.")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of input queries to process.")
    args = parser.parse_args()

    input_file = ROOT / "experiments/data/finetune/synthetic_queries.jsonl"
    output_file = ROOT / "experiments/data/finetune/synthetic_queries_augmented.jsonl"
    
    if not input_file.exists():
        print(f"Error: {input_file} not found. Run query generation first.")
        return

    # Load all input queries
    records = []
    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    
    print(f"Loaded {len(records)} existing queries from {input_file.name}.")
    if args.limit:
        records = records[:args.limit]
        print(f"Limited input to first {len(records)} queries.")

    if not records:
        print("No queries to process.")
        return

    # Prepare batches
    batches = []
    for i in range(0, len(records), args.batch_size):
        batches.append(records[i:i + args.batch_size])
    
    print(f"Split into {len(batches)} batches of size {args.batch_size}.")

    llm = get_internal_llm()
    write_lock = threading.Lock()
    
    system_prompt = (
        "Bạn là một sinh viên ngành Công nghệ Thông tin tại trường Đại học Công nghệ Thông tin (UIT).\n"
        "Nhiệm vụ của bạn là viết lại (paraphrase) danh sách câu hỏi học thuật ngắn gọn thành các câu hỏi tự nhiên, thực tế, "
        "giống văn phong thảo luận hoặc thắc mắc thực tế của sinh viên khi tự học hoặc làm bài tập."
    )

    completed_batches = 0
    total_batches = len(batches)

    def process_batch(batch_idx, batch_records):
        nonlocal completed_batches
        
        # Prepare the list of queries for the prompt
        formatted_queries = "\n".join([f"{idx+1}. {r['query']}" for idx, r in enumerate(batch_records)])
        
        human_prompt = (
            "Dưới đây là danh sách các câu hỏi ngắn gọn:\n"
            f"{formatted_queries}\n\n"
            "Hãy viết lại (paraphrase) từng câu hỏi trên thành một phiên bản mới tự nhiên hơn. Yêu cầu:\n"
            "1. Giữ nguyên ý nghĩa cốt lõi của câu hỏi để câu trả lời tương ứng vẫn chính xác.\n"
            "2. Làm câu hỏi tự nhiên hơn, có thể dài hơn (khoảng 15-20 từ), mang tính đào sâu bản chất hoặc thắc mắc thực tế của sinh viên.\n"
            "3. Sử dụng đan xen thuật ngữ tiếng Anh chuyên ngành (code-switching) giống cách sinh viên IT hay dùng (ví dụ: 'fit model', 'overfitting', 'loss function', 'bản chất của... là gì', 'tại sao lại dùng...').\n"
            "4. Trả về kết quả dưới dạng một danh sách JSON chứa đúng số lượng câu hỏi đã cho (JSON list of strings). Ví dụ: [\"câu hỏi 1 đã viết lại\", \"câu hỏi 2 đã viết lại\", ...]"
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]

        try:
            response_text = call_openai_with_retry(llm, messages)
            paraphrased_queries = parse_json_list(response_text)
            
            # If mismatch in count, retry once with strict request
            if len(paraphrased_queries) != len(batch_records):
                print(f"Warning: Batch {batch_idx+1} length mismatch ({len(paraphrased_queries)} vs {len(batch_records)}). Retrying...")
                retry_prompt = human_prompt + f"\nLưu ý: Hãy trả về CHÍNH XÁC {len(batch_records)} câu hỏi dưới dạng JSON list of strings."
                response_text = call_openai_with_retry(llm, [SystemMessage(content=system_prompt), HumanMessage(content=retry_prompt)])
                paraphrased_queries = parse_json_list(response_text)

            # Write out results
            with write_lock:
                with open(output_file, "a", encoding="utf-8") as out_f:
                    for idx, record in enumerate(batch_records):
                        # Write the original record first
                        out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                        
                        # Generate the augmented version
                        para_query = record["query"] # fallback to original if failed
                        if idx < len(paraphrased_queries):
                            para_query = paraphrased_queries[idx]
                        
                        augmented_record = record.copy()
                        augmented_record["query"] = para_query
                        augmented_record["is_augmented"] = True
                        
                        out_f.write(json.dumps(augmented_record, ensure_ascii=False) + "\n")
                    
                    out_f.flush()
            
            completed_batches += 1
            if completed_batches % 10 == 0 or completed_batches == total_batches:
                print(f"Progress: Completed {completed_batches}/{total_batches} batches ({(completed_batches/total_batches)*100:.1f}%).")
                
        except Exception as e:
            print(f"Error processing batch {batch_idx+1}: {e}")
            # Fallback: write original queries to ensure no loss of data
            with write_lock:
                with open(output_file, "a", encoding="utf-8") as out_f:
                    for record in batch_records:
                        out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                        out_f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # Clear output file if it exists (fresh start)
    if output_file.exists():
        output_file.unlink()

    print("Starting paraphrasing & query augmentation...")
    start_time = time.time()

    if args.workers > 1:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = [executor.submit(process_batch, idx, batch) for idx, batch in enumerate(batches)]
            for future in as_completed(futures):
                pass
    else:
        for idx, batch in enumerate(batches):
            process_batch(idx, batch)

    end_time = time.time()
    print(f"Query augmentation completed in {end_time - start_time:.2f} seconds.")
    
    # Count generated queries
    total_generated = 0
    if output_file.exists():
        with open(output_file, "r", encoding="utf-8") as f:
            total_generated = sum(1 for line in f if line.strip())
    print(f"Total queries written to {output_file.name}: {total_generated} queries.")

if __name__ == "__main__":
    main()
