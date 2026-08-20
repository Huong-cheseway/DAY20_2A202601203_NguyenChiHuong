# Benchmark Report

This report compares the same query set on single-agent baseline
and multi-agent workflow.
Quality is an automated structural proxy (0-10); peer review should validate it.

| Run | Latency (s) | Cost (USD) | Quality | Citation cov. | Failure rate | Notes |
|---|---:|---:|---:|---:|---:|---|
| single_agent | 4.79 | 0.0004 | 3.5 | 0% | 0% | averaged over 3 queries |
| multi_agent | 25.04 | 0.0010 | 10.0 | 100% | 0% | averaged over 3 queries |

## Key Findings

- Fastest run: **single_agent** (4.79s).
- Lowest estimated cost: **single_agent** (0.0004 USD).
- Highest quality score: **multi_agent** (10.00/10).

## Trade-off Notes

- Multi-agent can be slower or more expensive because it performs
  more handoffs and checks.
- This is expected behavior, not a bug, when quality/citation robustness improves.
- Prefer baseline for simple requests; prefer multi-agent
  when evidence synthesis matters.

## Failure Mode and Mitigation

- During this real Groq benchmark, several requests received HTTP 429 rate-limit responses.
- The bounded retry policy honored Groq's delay (7-28 seconds) and all six benchmark runs
  eventually completed; failure rate remained 0%.
- This explains much of the multi-agent latency. For larger suites, throttle requests,
  reduce output size, or add a delay between queries.
- The offline corpus contains retrieval/evidence-grounding material but no direct GraphRAG
  primary source. The workflow now reports this evidence gap instead of inventing support.

## Trace Evidence

- Local span log: `reports/trace_spans.jsonl`
- Verified LangSmith trace:
  https://smith.langchain.com/o/0a3f2792-f66a-4a48-ae6d-e560742584ea/projects/p/73eb0c4c-bc6c-4a1a-9ea3-6ee754c1e89c/r/01a01d8d-426f-7213-80f3-c5fe365beb04?poll=true
- Project: `multi-agent-research-lab`; verified spans include Supervisor, Researcher,
  Analyst, Writer, and benchmark wrappers with `error=False`.
