# Kế hoạch tối ưu RAG và hoàn thiện observability

## Mục tiêu

Sửa đúng reranker trước khi tối ưu, bổ sung trace đủ để giải thích toàn bộ `chat_stream`, khôi phục CPU/RAM/GPU trên Grafana bền vững sau reboot, và dùng **chính lần gọi Jev supervisor hiện có** để quyết định có chạy query expansion hay không.

## Kế hoạch thực thi cho agent

Giao Luna Max ALM2 theo thứ tự và prompt trong [`docs/superpowers/plans/2026-09-29-rag-observability-handoff.md`](docs/superpowers/plans/2026-09-29-rag-observability-handoff.md). Mỗi lần chỉ giao một plan:

1. [`2026-09-29-reranker-query-correctness.md`](docs/superpowers/plans/2026-09-29-reranker-query-correctness.md)
2. [`2026-09-29-request-tracing-token-cost.md`](docs/superpowers/plans/2026-09-29-request-tracing-token-cost.md)
3. [`2026-09-29-windows-host-metrics.md`](docs/superpowers/plans/2026-09-29-windows-host-metrics.md)
4. [`2026-09-29-jev-query-expansion-gate.md`](docs/superpowers/plans/2026-09-29-jev-query-expansion-gate.md)
5. [`2026-09-29-rag-latency-ablation.md`](docs/superpowers/plans/2026-09-29-rag-latency-ablation.md)

## Bằng chứng hiện tại

- Prometheus và Grafana đang chạy; target API `up`, nhưng target `windows` trả `connection refused` và `up{job="windows"}=0`. Máy không có process/service `windows_exporter`; tài liệu cũ xác nhận hôm qua chỉ chạy bản portable trong phiên hiện tại, chưa cài service tự khởi động. Vì vậy toàn bộ CPU/RAM/GPU Windows cùng mất; đây không phải lỗi panel Grafana.
- `chat_stream - puq-chat-workflow` chưa được tách span: khoảng 2.4–2.7s lúc warm và 10.81s ở request đầu sau restart. Vùng này gồm DB history/commit, semantic-cache lookup/write và SSE finalize.
- Reranker OpenVINO/ONNX/PyTorch bỏ qua query: `score_pairs(query, texts)` gọi scorer chỉ với `texts`; hai query khác nhau cho score giống hệt nhau.
- Mỗi câu hỏi Tutor tạo 3 query bổ sung, lấy 315–320 raw docs, giữ tối đa 60, rerank 46–49 rồi trả 10. `rag_rerank` mất khoảng 11.3s. `EnsembleRetriever(k=40)` không thực sự cap output vì phiên bản LangChain hiện tại không có tham số `k`.

## Quyết định thiết kế

1. **Jev expansion gate:** thêm câu hỏi typed `query_expansion=skip|expand` vào payload `/v1/systemone`; chỉ gắn `expand_query` vào args của `AskTutor`. Không gọi Jev lần hai. Nếu Jev lỗi/Luna không trả trường này, mặc định `expand_query=true` để bảo toàn recall hiện tại.
2. **Observability hai tầng:** Langfuse cho critical path của từng request; Prometheus/Grafana cho p50/p95 và xu hướng. Không gửi query, document hay context vào span con; chỉ cho metadata enum/số lượng có giới hạn.
3. **Windows host metrics:** cài `windows_exporter` native thành Windows service `Automatic`; Docker Compose chỉ scrape nó qua `host.docker.internal:9182`. Không cố chạy exporter Windows trong Linux container.
4. **Tối ưu sau correctness:** chỉ giảm candidate/context khi benchmark retrieval đạt quality gate; không lấy latency đổi chất lượng mà không đo.

## Công việc theo thứ tự ưu tiên

- [x] **P0 — Sửa reranker dùng đúng query.** Đổi scorer contract trong `src/retrieval/reranking.py` thành `_score_batch(query, batch)` cho OpenVINO, ONNX, TensorRT và PyTorch; tokenizer phải nhận `[query] * batch_size` cùng documents. Thêm regression test bắt query propagation và smoke thực với cùng documents/hai query khác nhau. → Verify: `pytest -q tests/retrieval/test_reranker_backends.py`; score/order phải thay đổi theo query.

- [x] **P0 — Trace và usage đầy đủ toàn request.** Giữ span `puq-chat-workflow` hiện có; trong `backend/app/services/chat.py` bổ sung các sibling spans `history_load`, `user_message_commit`, `semantic_cache_get`, `assistant_message_commit`, `semantic_cache_set`, `sse_finalize`, đồng thời thêm histogram stage có label hữu hạn trong `src/shared/metrics.py`. Trong retrieval, gắn metadata đếm vào `retrieve_context`/`rag_rerank` thay vì tạo span trùng. Từ các event `on_chat_model_end`, cộng `input_tokens`/`output_tokens` đúng một lần theo `run_id` vào `_StreamTelemetry` và root metadata; không ghi lại chúng thành root `usage_details` để tránh Langfuse cộng đôi với generation children. Instrument semantic-cache embedding như observation có usage/cost thật; Jev chỉ được tính cost khi provider trả usage/cost, nếu không root phải ghi `cost_coverage=partial` và số external calls chưa định giá. Mở rộng allowlist ở `src/shared/observability.py` chỉ cho metadata enum/số lượng có giới hạn (`cache_result`, document counts, reranker backend, context chars, expansion decision, token totals, generation count, cost coverage); không cho prompt/context ở child span. → Verify: InMemorySpanExporter cho thấy đúng hierarchy, token tổng bằng tổng các generation duy nhất, không double-count, trace chỉ báo total cost khi coverage đầy đủ, privacy canaries không xuất hiện; `pytest -q tests/api/test_tracing_privacy.py tests/api/test_chat_stream.py`.

- [ ] **P0 — Khôi phục host metrics bền vững.** Thêm `scripts/setup-windows-exporter.ps1` chạy một lần với Administrator: tải/pin `windows_exporter` chính thức, kiểm checksum, cài service tự động với CPU, memory và GPU collectors, chỉ mở cổng 9182 cho local/Docker Desktop. `dev.ps1 up/status` kiểm tra target và in hướng dẫn rõ nếu exporter thiếu/thất bại, không âm thầm báo stack khỏe. → Verify sau reboot: service `Running/Automatic`, `up{job="windows"}=1`, có `windows_cpu_time_total`, memory series, `windows_gpu_engine_time_seconds` và GPU memory series; panel Grafana CPU/RAM/GPU có dữ liệu thật.

- [ ] **P1 — Dùng Jev quyết định query expansion trong cùng request supervisor.** Cập nhật `src/generation/jev_router.py` với typed choice và tiêu chí: `skip` cho câu hỏi ngắn, tự đủ nghĩa, khái niệm/công thức rõ; `expand` cho đại từ phụ thuộc lịch sử, câu mơ hồ, đa ý hoặc cần synonym. Cập nhật `AskTutor` tool/state trong `src/rag_core/lang_graph_rag.py`, truyền cờ qua `src/rag_core/agents/tutor.py` tới `Offline_RAG.get_context`; khi skip dùng duy nhất query gốc. Ghi decision vào trace/metric nhưng không ghi query. → Verify: mock Jev chỉ có một HTTP request; câu “decision tree là gì” skip, câu “nó khác cái trên thế nào” expand; Jev/Luna fallback vẫn chạy expansion như trước. Chạy `pytest -q tests/generation/test_jev_router.py tests/rag_core/test_lang_graph_rag.py`.

- [x] **P1 — Benchmark và giới hạn candidate có quality gate.** Sau khi reranker đúng, benchmark production workload với pool 60/48/40/32/24 và batch size 8/16; cap fused candidates trước rerank thay vì tính nhiều candidates rồi bỏ phần lớn. So với pool 60 cùng batch, chỉ nhận cấu hình nhỏ hơn khi NDCG@10 giảm không quá 0.005, MRR@10 giảm không quá 0.01, Recall@10 và Hit@5 mỗi metric giảm không quá 0.005, đồng thời p95 rerank cải thiện ít nhất 20%. Không dùng gate Recall@40 cho pool nhỏ hơn 40 vì pool reduction chủ động loại candidates. Ghi kết quả vào `docs/reranker-cpu-int8-openvino-research.md` và báo cáo ablation. → Human gate chọn batch 8, pool 24; production đặt `RAG_RERANK_CANDIDATE_LIMIT=24`.
  - Evidence 2026-09-30: pool 24 PASS trên 20 query (`p95=8.018s`, cải thiện `59.7%`); pool 32 cũng PASS nhưng chậm hơn; pool 40/48 REJECT; batch 16 REJECT vì vi phạm batch parity. Bảng: `experiments/runs/reranker_runtime/corrected_query_matrix_20/summary.md`.

- [ ] **P1 — Tách cold start và cache overhead.** Cho startup prewarm chạy một embedding, một Chroma search và một rerank batch nhỏ; không gọi provider trả phí trong prewarm. Chuyển phần sync của semantic cache khỏi event loop, tái sử dụng embedding client thay vì tạo `OpenAIEmbeddings` mỗi request; chỉ quyết định background cache write nếu span chứng minh nó nằm sau answer và có cơ chế shutdown an toàn. → Verify: request đầu và 5 request warm có stage spans; vector retrieval cold gần warm, event loop không bị block, cache hit/miss và DB persistence không đổi.

- [x] **P2 — Giảm context final LLM sau ablation.** So sánh top 10/7/5 docs dựa trên answer correctness, citation validity, token input, TTFT và generation p95. Chỉ cut over nếu chất lượng đạt gate; không kiểm bằng độ dài output đơn thuần. → Human gate 2 đã duyệt cắt về top 5; production đặt `RAG_CONTEXT_TOP_K=5`.
  - Benchmark 2026-10-03 (candidate cap 24, 20 câu hỏi): citation valid `20/20` cả ba mức; input tokens giảm 39% (mean 2,406 vs 3,944); tổng thời gian giảm 35% (mean 8.95s vs 13.72s). Bảng: `experiments/runs/tutor_context/summary.md`.

- [ ] **P3 — Hoàn thiện dashboard và kiểm thử end-to-end.** Thêm panel chat-stage p50/p95, cold-vs-warm, expansion skip/expand, rerank input count/backend; giữ panel host CPU/RAM/GPU và target health. Chạy full Python tests, Docker rebuild CPU, mở web gửi ba query cold/warm, kiểm Langfuse tree thực, Prometheus targets và Grafana bằng browser. Cập nhật checklist/kết quả ngay trong file kế hoạch này. → Verify: `pytest -q tests`; `docker compose` services healthy; API + Windows targets `UP`; dashboard có samples; trace không còn khoảng thời gian lớn không giải thích được.

## Thứ tự phụ thuộc

```text
Reranker correctness ──> candidate/batch benchmark ──> context ablation
Trace coverage ────────> cache/cold-start optimization ──> dashboard stage panels
Windows exporter service ────────────────────────────────> CPU/RAM/GPU panels
Jev typed decision ────> tutor expansion gate ───────────> expansion latency ablation
```

## Hoàn tất khi

- Reranker thay đổi score theo query và đạt quality gate.
- Mỗi request Langfuse giải thích được DB/cache/workflow/SSE critical path, hiển thị input/output/total tokens ở root, và phân biệt rõ cost đầy đủ với cost thiếu Jev/embedding mà không lộ nội dung retrieval.
- Sau reboot, `windows_exporter` tự chạy và Grafana có CPU/RAM/GPU.
- Query đơn giản bỏ được call expansion; query phụ thuộc lịch sử vẫn expand; không phát sinh Jev request thứ hai.
- Ba query mẫu có warm latency giảm, cold-start spike được loại hoặc giải thích bằng span, toàn bộ test và smoke Docker đều đạt.
