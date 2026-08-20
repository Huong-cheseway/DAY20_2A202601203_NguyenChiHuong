# Thiết kế hệ thống

## Bài toán

Hệ thống nhận một câu hỏi nghiên cứu, tìm nguồn trong corpus offline, đánh giá độ tin cậy,
tổng hợp câu trả lời có citation và lưu trace để so sánh với single-agent baseline.

## Vì sao dùng multi-agent?

Bài toán có ba artefact khác nhau: nguồn, phân tích độ tin cậy và bản viết cuối. Tách vai trò
giúp kiểm tra từng handoff, phát hiện nguồn yếu và đo chi phí từng bước. Với câu hỏi ngắn,
single-agent vẫn phù hợp hơn vì ít latency và chi phí hơn.

## Vai trò

| Agent | Trách nhiệm | Input | Output | Failure mode |
|---|---|---|---|---|
| Supervisor | Chọn bước tiếp theo và dừng workflow | Toàn bộ shared state | Route tiếp theo | Vòng lặp; chặn bằng max iterations |
| Researcher | Tìm và xếp hạng nguồn offline | Query, max_sources | Sources, research_notes | Không có corpus; dùng tài liệu fallback |
| Analyst | So sánh và đánh giá nguồn | Query, sources | analysis_notes | LLM lỗi/rate limit; retry rồi deterministic fallback |
| Writer | Viết đúng câu hỏi và gắn citation | Query, analysis, sources | final_answer | LLM lỗi/rate limit; retry rồi deterministic fallback |

## Shared state

- `request`: query, audience và giới hạn nguồn.
- `iteration`, `route_history`: kiểm soát vòng lặp và giải thích routing.
- `sources`, `research_notes`, `analysis_notes`, `final_answer`: artefact handoff.
- `agent_results`: metadata model, token, cost và trạng thái fallback.
- `trace`, `errors`: quan sát và chẩn đoán lỗi.

## Routing policy

```text
START -> Supervisor
  thiếu sources        -> Researcher -> Supervisor
  thiếu analysis_notes -> Analyst    -> Supervisor
  chưa có final_answer -> Writer     -> Supervisor
  có answer/lỗi/quá max_iterations   -> END
```

## Guardrails

- Max iterations: 6.
- Timeout: 60 giây cho mỗi async worker node và HTTP provider call.
- Retry: tối đa 2 lần ở LLM client; LangGraph có bounded retry policy.
- Fallback: Analyst/Writer dùng kết quả deterministic và ghi `fallback_used`.
- Validation: Pydantic kiểm tra query, sources, state và benchmark metrics.

## Benchmark plan

- Ba query trong `configs/lab_default.yaml` chạy qua cả baseline và multi-agent.
- Metrics: latency, token/cost Groq, quality proxy, citation coverage, failure rate.
- Kỳ vọng: baseline nhanh/rẻ hơn; multi-agent có citation và trace tốt hơn.
- Quality proxy phải được xác nhận bằng peer review, không coi là ground truth.
