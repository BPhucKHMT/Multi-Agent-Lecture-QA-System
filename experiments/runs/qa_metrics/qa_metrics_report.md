# QA Metrics Benchmark Report

## Answerable QA quality

| Config | Chunk family | BERTScore F1 | Faithfulness | Answer relevancy | Context precision | Context recall | Mean latency |
|---|---|---:|---:|---:|---:|---:|---:|
| C21 | timestamp150 | 0.8023 | 0.9586 | 0.5379 | 0.9419 | 0.9512 | 1.5030 |
| C22 | parent-child | 0.8023 | 0.9526 | 0.5360 | 0.9510 | 0.9588 | 1.8009 |
| C19 | semantic | 0.8109 | 0.9566 | 0.5399 | 0.8611 | 0.9008 | 1.3253 |
| C02 | recursive | 0.8102 | 0.9492 | 0.5421 | 0.8968 | 0.9158 | 1.5564 |

## No-answer robustness

| Config | Chunk family | Refusal accuracy | False answer rate | Exact template rate | Mean latency |
|---|---|---:|---:|---:|---:|
| C21 | timestamp150 | 1.0000 | 0.0000 | 1.0000 | 1.5030 |
| C22 | parent-child | 1.0000 | 0.0000 | 1.0000 | 1.8009 |
| C19 | semantic | 1.0000 | 0.0000 | 1.0000 | 1.3253 |
| C02 | recursive | 1.0000 | 0.0000 | 1.0000 | 1.5564 |
