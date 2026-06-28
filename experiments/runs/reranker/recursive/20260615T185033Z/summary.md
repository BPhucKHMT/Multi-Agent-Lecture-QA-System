# Reranker Benchmark Summary

## Candidate Metrics

- `query_count`: 1800
- `sources`: {'BAAI/bge-m3': {'query_count': 300, 'no_qrels_query_count': 0, 'recall@40': 0.5265239066489067, 'mrr@10': 0.6301706349206349, 'ndcg@10': 0.44042821593235343}, 'BAAI/bge-m3-finetuned': {'query_count': 300, 'no_qrels_query_count': 0, 'recall@40': 0.5355869547119547, 'mrr@10': 0.5848915343915344, 'ndcg@10': 0.4088645856612054}, 'intfloat/multilingual-e5-large': {'query_count': 300, 'no_qrels_query_count': 0, 'recall@40': 0.5384313510563511, 'mrr@10': 0.6569880952380952, 'ndcg@10': 0.4464064852755051}, 'bkai-foundation-models/vietnamese-bi-encoder': {'query_count': 300, 'no_qrels_query_count': 0, 'recall@40': 0.369621225996226, 'mrr@10': 0.4382208994708995, 'ndcg@10': 0.28013839245905015}, 'dangvantuan/vietnamese-embedding': {'query_count': 300, 'no_qrels_query_count': 0, 'recall@40': 0.24019670607170607, 'mrr@10': 0.28552248677248676, 'ndcg@10': 0.1722914029139554}, 'contextboxai/halong_embedding': {'query_count': 300, 'no_qrels_query_count': 0, 'recall@40': 0.5168065684315684, 'mrr@10': 0.5955529100529101, 'ndcg@10': 0.403114312416789}}

## Runs

| Embedding | Reranker | Pool | Status | NDCG@10 | MRR@10 | Recall@40 | P95 ms | Latency |
|---|---|---:|---|---:|---:|---:|---:|---|
| BAAI/bge-m3 | no_rerank | 40 | completed | 0.44042821593235343 | 0.6301706349206349 | 0.5265239066489067 | 0.00540503824595362 | pass |
| BAAI/bge-m3-finetuned | no_rerank | 40 | completed | 0.4088645856612054 | 0.5848915343915344 | 0.5355869547119547 | 0.0046999804908409715 | pass |
| intfloat/multilingual-e5-large | no_rerank | 40 | completed | 0.4464064852755051 | 0.6569880952380952 | 0.5384313510563511 | 0.00640999060124159 | pass |
| bkai-foundation-models/vietnamese-bi-encoder | no_rerank | 40 | completed | 0.28013839245905015 | 0.4382208994708995 | 0.369621225996226 | 0.005599984433501959 | pass |
| dangvantuan/vietnamese-embedding | no_rerank | 40 | completed | 0.1722914029139554 | 0.28552248677248676 | 0.24019670607170607 | 0.0037999707274138927 | pass |
| contextboxai/halong_embedding | no_rerank | 40 | completed | 0.403114312416789 | 0.5955529100529101 | 0.5168065684315684 | 0.003800028935074806 | pass |
| BAAI/bge-m3 | cross-encoder/ms-marco-MiniLM-L-6-v2 | 40 | completed | 0.3197689182072641 | 0.4680449735449736 | 0.5265239066489067 | 134.5918750099372 | pass |
| BAAI/bge-m3-finetuned | cross-encoder/ms-marco-MiniLM-L-6-v2 | 40 | completed | 0.3235969029363205 | 0.46937830687830684 | 0.5355869547119547 | 135.71835997281596 | pass |
| intfloat/multilingual-e5-large | cross-encoder/ms-marco-MiniLM-L-6-v2 | 40 | completed | 0.32905702879294685 | 0.48167989417989415 | 0.5384313510563511 | 135.3202199767111 | pass |
| bkai-foundation-models/vietnamese-bi-encoder | cross-encoder/ms-marco-MiniLM-L-6-v2 | 40 | completed | 0.2691960761192982 | 0.4242222222222222 | 0.369621225996226 | 134.04935500584543 | pass |
| dangvantuan/vietnamese-embedding | cross-encoder/ms-marco-MiniLM-L-6-v2 | 40 | completed | 0.22176303821706678 | 0.377484126984127 | 0.24019670607170607 | 135.0792349956464 | pass |
| contextboxai/halong_embedding | cross-encoder/ms-marco-MiniLM-L-6-v2 | 40 | completed | 0.3149872752279791 | 0.4776917989417989 | 0.5168065684315684 | 136.31666001456324 | pass |
| BAAI/bge-m3 | BAAI/bge-reranker-base | 40 | completed | 0.40979541583298995 | 0.5992460317460317 | 0.5265239066489067 | 524.2808150069322 | pass |
| BAAI/bge-m3-finetuned | BAAI/bge-reranker-base | 40 | completed | 0.40976262183860807 | 0.5933015873015873 | 0.5355869547119547 | 523.2812800299143 | pass |
| intfloat/multilingual-e5-large | BAAI/bge-reranker-base | 40 | completed | 0.41476993697361825 | 0.6017910052910053 | 0.5384313510563511 | 524.3306600488722 | pass |
| bkai-foundation-models/vietnamese-bi-encoder | BAAI/bge-reranker-base | 40 | completed | 0.3405031711476738 | 0.5252526455026455 | 0.369621225996226 | 519.5973650203086 | pass |
| dangvantuan/vietnamese-embedding | BAAI/bge-reranker-base | 40 | completed | 0.26530772510909006 | 0.43688095238095237 | 0.24019670607170607 | 517.9696900246199 | pass |
| contextboxai/halong_embedding | BAAI/bge-reranker-base | 40 | completed | 0.41573912894900783 | 0.6029126984126983 | 0.5168065684315684 | 521.0716750269057 | pass |
| BAAI/bge-m3 | BAAI/bge-reranker-v2-m3 | 40 | completed | 0.5057694907366248 | 0.7364021164021164 | 0.5265239066489067 | 1722.1388200006913 | reject |
| BAAI/bge-m3-finetuned | BAAI/bge-reranker-v2-m3 | 40 | completed | 0.5041301240411323 | 0.7275648148148148 | 0.5355869547119547 | 1715.7179599773372 | reject |
| intfloat/multilingual-e5-large | BAAI/bge-reranker-v2-m3 | 40 | completed | 0.5091502591405336 | 0.7345026455026455 | 0.5384313510563511 | 1736.666879997938 | reject |
| bkai-foundation-models/vietnamese-bi-encoder | BAAI/bge-reranker-v2-m3 | 40 | completed | 0.41480772526452003 | 0.6471362433862434 | 0.369621225996226 | 1715.4516250098823 | reject |
| dangvantuan/vietnamese-embedding | BAAI/bge-reranker-v2-m3 | 40 | completed | 0.3067201952042145 | 0.526957671957672 | 0.24019670607170607 | 1708.9944649982501 | reject |
| contextboxai/halong_embedding | BAAI/bge-reranker-v2-m3 | 40 | completed | 0.4974346990557529 | 0.7268412698412698 | 0.5168065684315684 | 1719.3942200159654 | reject |
| BAAI/bge-m3 | jinaai/jina-reranker-v2-base-multilingual | 40 | completed | 0.5030111124878042 | 0.7395965608465609 | 0.5265239066489067 | 178.00355002109427 | pass |
| BAAI/bge-m3-finetuned | jinaai/jina-reranker-v2-base-multilingual | 40 | completed | 0.5070493500908408 | 0.7386243386243386 | 0.5355869547119547 | 177.85284501151182 | pass |
| intfloat/multilingual-e5-large | jinaai/jina-reranker-v2-base-multilingual | 40 | completed | 0.5039126419471386 | 0.734989417989418 | 0.5384313510563511 | 179.33506504341494 | pass |
| bkai-foundation-models/vietnamese-bi-encoder | jinaai/jina-reranker-v2-base-multilingual | 40 | completed | 0.412866722272962 | 0.6478227513227514 | 0.369621225996226 | 177.8835949866334 | pass |
| dangvantuan/vietnamese-embedding | jinaai/jina-reranker-v2-base-multilingual | 40 | completed | 0.31043758425615975 | 0.5397222222222222 | 0.24019670607170607 | 175.33727001282386 | pass |
| contextboxai/halong_embedding | jinaai/jina-reranker-v2-base-multilingual | 40 | completed | 0.4952747954759219 | 0.7299246031746032 | 0.5168065684315684 | 178.05960995610806 | pass |
| BAAI/bge-m3 | experiments/runs/finetune/reranker/20260616-012511 | 40 | completed | 0.4322006603147303 | 0.638829365079365 | 0.5265239066489067 | 178.98968002700713 | pass |
| BAAI/bge-m3-finetuned | experiments/runs/finetune/reranker/20260616-012511 | 40 | completed | 0.4181583440680344 | 0.6215780423280423 | 0.5355869547119547 | 176.66775501857046 | pass |
| intfloat/multilingual-e5-large | experiments/runs/finetune/reranker/20260616-012511 | 40 | completed | 0.4273771065122514 | 0.6423849206349206 | 0.5384313510563511 | 178.9208849950228 | pass |
| bkai-foundation-models/vietnamese-bi-encoder | experiments/runs/finetune/reranker/20260616-012511 | 40 | completed | 0.35185957526327893 | 0.5643465608465609 | 0.369621225996226 | 177.56392999435775 | pass |
| dangvantuan/vietnamese-embedding | experiments/runs/finetune/reranker/20260616-012511 | 40 | completed | 0.2554168621589187 | 0.4310753968253968 | 0.24019670607170607 | 175.89182498923037 | pass |
| contextboxai/halong_embedding | experiments/runs/finetune/reranker/20260616-012511 | 40 | completed | 0.4303373318781771 | 0.6361230158730158 | 0.5168065684315684 | 179.4897849933477 | pass |
| BAAI/bge-m3 | namdp-ptit/ViRanker | 40 | completed | 0.47807395540490527 | 0.699978835978836 | 0.5265239066489067 | 1687.5141949974932 | reject |
| BAAI/bge-m3-finetuned | namdp-ptit/ViRanker | 40 | completed | 0.48754571383191814 | 0.6966362433862433 | 0.5355869547119547 | 1683.6959000123898 | reject |
| intfloat/multilingual-e5-large | namdp-ptit/ViRanker | 40 | completed | 0.48242422140692487 | 0.6959404761904762 | 0.5384313510563511 | 1676.2821749929572 | reject |
| bkai-foundation-models/vietnamese-bi-encoder | namdp-ptit/ViRanker | 40 | completed | 0.4006236599802864 | 0.623271164021164 | 0.369621225996226 | 1659.7836550034117 | reject |
| dangvantuan/vietnamese-embedding | namdp-ptit/ViRanker | 40 | completed | 0.2957668043368237 | 0.5022063492063492 | 0.24019670607170607 | 1658.1613349932013 | reject |
| contextboxai/halong_embedding | namdp-ptit/ViRanker | 40 | completed | 0.4759917553919594 | 0.6876772486772487 | 0.5168065684315684 | 1671.305784973083 | reject |

## Config

- Dataset: `phase4_reranker_final_slide_v1`
- Strategy: `recursive`
