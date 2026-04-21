#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage:
  bash scripts/collect_metrics.sh <log-file>
  docker compose logs --no-color gameserver | bash scripts/collect_metrics.sh -

The script parses GameServer logs that contain:
  - step=request_summary
  - step=slow_request_alert

Output is a Markdown summary for interview notes or docs.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 0
fi

input_path="${1:--}"
raw_log="$(mktemp)"
summary_tsv="$(mktemp)"
trap 'rm -f "$raw_log" "$summary_tsv"' EXIT

if [[ "$input_path" == "-" ]]; then
    cat > "$raw_log"
else
    if [[ ! -f "$input_path" ]]; then
        echo "Log file not found: $input_path" >&2
        exit 1
    fi
    cat "$input_path" > "$raw_log"
fi

awk '
function value(name, fallback,    i, key) {
    for (i = 1; i <= NF; i++) {
        split($i, pair, "=")
        key = pair[1]
        if (key == name) {
            return substr($i, length(key) + 2)
        }
    }
    return fallback
}

$0 ~ /step=request_summary/ {
    print value("trace", ""), \
          value("model", "unknown"), \
          value("total_ms", "0"), \
          value("first_token_ms", "-1"), \
          value("rag_ms", "0"), \
          value("llm_ms", "0"), \
          value("tool_ms", "0"), \
          value("rag_chunks", "0"), \
          value("input_tokens", "0"), \
          value("output_tokens", "0"), \
          value("cost_usd", "0"), \
          value("llm_calls", "0"), \
          value("tool_calls", "0"), \
          value("tool_success_count", "0"), \
          value("tool_failure_count", "0"), \
          value("stream_success", "0"), \
          value("fallback_used", "0")
}
' "$raw_log" > "$summary_tsv"

sample_count="$(wc -l < "$summary_tsv" | tr -d ' ')"
if [[ "$sample_count" == "0" ]]; then
    echo "No step=request_summary lines found in input." >&2
    exit 1
fi

slow_count="$(grep -c 'step=slow_request_alert' "$raw_log" || true)"

avg_col() {
    local col="$1"
    awk -v col="$col" '{sum += $col} END {if (NR == 0) {print "0.0"} else {printf "%.2f", sum / NR}}' "$summary_tsv"
}

sum_col() {
    local col="$1"
    awk -v col="$col" '{sum += $col} END {printf "%.6f", sum}' "$summary_tsv"
}

percentile_col() {
    local col="$1"
    local percentile="$2"
    awk -v col="$col" "{print \$col}" "$summary_tsv" | LC_ALL=C sort -n | awk -v p="$percentile" '
        { values[++n] = $1 }
        END {
            if (n == 0) {
                print "n/a"
                exit
            }
            idx = int((p * n + 99) / 100)
            if (idx < 1) idx = 1
            if (idx > n) idx = n
            printf "%.2f", values[idx]
        }
    '
}

percentile_positive_col() {
    local col="$1"
    local percentile="$2"
    awk -v col="$col" '$col >= 0 {print $col}' "$summary_tsv" | LC_ALL=C sort -n | awk -v p="$percentile" '
        { values[++n] = $1 }
        END {
            if (n == 0) {
                print "n/a"
                exit
            }
            idx = int((p * n + 99) / 100)
            if (idx < 1) idx = 1
            if (idx > n) idx = n
            printf "%.2f", values[idx]
        }
    '
}

first_token_coverage="$(awk '$4 >= 0 {count++} END {print count + 0}' "$summary_tsv")"
rag_hit_count="$(awk '$8 > 0 {count++} END {print count + 0}' "$summary_tsv")"

avg_total_ms="$(avg_col 3)"
p50_total_ms="$(percentile_col 3 50)"
p95_total_ms="$(percentile_col 3 95)"
avg_first_token_ms="$(awk '$4 >= 0 {sum += $4; count++} END {if (count == 0) {print "n/a"} else {printf "%.2f", sum / count}}' "$summary_tsv")"
p50_first_token_ms="$(percentile_positive_col 4 50)"
p95_first_token_ms="$(percentile_positive_col 4 95)"
avg_rag_ms="$(avg_col 5)"
avg_llm_ms="$(avg_col 6)"
avg_tool_ms="$(avg_col 7)"
avg_input_tokens="$(avg_col 9)"
avg_output_tokens="$(avg_col 10)"
avg_llm_calls="$(avg_col 12)"
avg_tool_calls="$(avg_col 13)"
avg_tool_success_count="$(avg_col 14)"
avg_tool_failure_count="$(avg_col 15)"
avg_cost_usd="$(avg_col 11)"
total_cost_usd="$(sum_col 11)"
slow_rate="$(awk -v slow="$slow_count" -v total="$sample_count" 'BEGIN {printf "%.2f", (slow / total) * 100}')"
rag_hit_rate="$(awk -v hit="$rag_hit_count" -v total="$sample_count" 'BEGIN {printf "%.2f", (hit / total) * 100}')"
first_token_rate="$(awk -v hit="$first_token_coverage" -v total="$sample_count" 'BEGIN {printf "%.2f", (hit / total) * 100}')"
stream_success_count="$(awk '$16 == 1 {count++} END {print count + 0}' "$summary_tsv")"
fallback_count="$(awk '$17 == 1 {count++} END {print count + 0}' "$summary_tsv")"
stream_success_rate="$(awk -v hit="$stream_success_count" -v total="$sample_count" 'BEGIN {printf "%.2f", (hit / total) * 100}')"
fallback_rate="$(awk -v hit="$fallback_count" -v total="$sample_count" 'BEGIN {printf "%.2f", (hit / total) * 100}')"
tool_success_rate="$(awk '{success += $14; failure += $15} END {total = success + failure; if (total == 0) {print "n/a"} else {printf "%.2f", (success / total) * 100}}' "$summary_tsv")"

cat <<EOF
# Metrics Summary

- Source: ${input_path}
- Samples: ${sample_count}
- Slow request alerts: ${slow_count} (${slow_rate}%)
- First token coverage: ${first_token_coverage}/${sample_count} (${first_token_rate}%)
- Stream success rate: ${stream_success_count}/${sample_count} (${stream_success_rate}%)
- Fallback usage rate: ${fallback_count}/${sample_count} (${fallback_rate}%)

| Metric | Value |
|---|---|
| Avg total latency | ${avg_total_ms} ms |
| P50 total latency | ${p50_total_ms} ms |
| P95 total latency | ${p95_total_ms} ms |
| Avg first token latency | ${avg_first_token_ms} ms |
| P50 first token latency | ${p50_first_token_ms} ms |
| P95 first token latency | ${p95_first_token_ms} ms |
| Avg RAG latency | ${avg_rag_ms} ms |
| RAG hit rate | ${rag_hit_rate}% |
| Avg LLM latency | ${avg_llm_ms} ms |
| Avg tool latency | ${avg_tool_ms} ms |
| Avg input tokens | ${avg_input_tokens} |
| Avg output tokens | ${avg_output_tokens} |
| Avg LLM calls / request | ${avg_llm_calls} |
| Avg tool calls / request | ${avg_tool_calls} |
| Avg successful tool calls / request | ${avg_tool_success_count} |
| Avg failed tool calls / request | ${avg_tool_failure_count} |
| Tool success rate | ${tool_success_rate}% |
| Avg estimated cost / request | \$${avg_cost_usd} |
| Total estimated cost | \$${total_cost_usd} |

## Model Breakdown

| Model | Requests | Share |
|---|---|---|
EOF

awk '{count[$2]++} END {for (model in count) print model "\t" count[model]}' "$summary_tsv" | LC_ALL=C sort -k2,2nr -k1,1 | \
while IFS=$'\t' read -r model count; do
    share="$(awk -v current="$count" -v total="$sample_count" 'BEGIN {printf "%.2f", (current / total) * 100}')"
    printf '| `%s` | %s | %s%% |\n' "$model" "$count" "$share"
done

cat <<'EOF'

## Slowest Requests

| Trace | Model | Total Latency (ms) | First Token (ms) | Tool Calls | Fallback |
|---|---|---|---|---|---|
EOF

LC_ALL=C sort -k3,3nr "$summary_tsv" | head -n 5 | \
awk '{printf("| `%s` | `%s` | %.2f | %.2f | %s | %s |\n", $1, $2, $3, $4, $13, ($17 == 1 ? "yes" : "no"))}'
