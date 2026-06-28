# Reranker Benchmark Summary

## Candidate Metrics

- `query_count`: 1500
- `sources`: {'BAAI/bge-m3': {'query_count': 300, 'no_qrels_query_count': 0, 'recall@40': 0.5265239066489067, 'mrr@10': 0.6301706349206349, 'ndcg@10': 0.44042821593235343}, 'intfloat/multilingual-e5-large': {'query_count': 300, 'no_qrels_query_count': 0, 'recall@40': 0.5384313510563511, 'mrr@10': 0.6569880952380952, 'ndcg@10': 0.4464064852755051}, 'bkai-foundation-models/vietnamese-bi-encoder': {'query_count': 300, 'no_qrels_query_count': 0, 'recall@40': 0.369621225996226, 'mrr@10': 0.4382208994708995, 'ndcg@10': 0.28013839245905015}, 'dangvantuan/vietnamese-embedding': {'query_count': 300, 'no_qrels_query_count': 0, 'recall@40': 0.24019670607170607, 'mrr@10': 0.28552248677248676, 'ndcg@10': 0.1722914029139554}, 'contextboxai/halong_embedding': {'query_count': 300, 'no_qrels_query_count': 0, 'recall@40': 0.5168065684315684, 'mrr@10': 0.5955529100529101, 'ndcg@10': 0.403114312416789}}

## Runs

| Embedding | Reranker | Pool | Status | NDCG@10 | MRR@10 | Recall@40 | P95 ms | Latency |
|---|---|---:|---|---:|---:|---:|---:|---|
| BAAI/bge-m3 | no_rerank | 40 | completed | 0.44042821593235343 | 0.6301706349206349 | 0.5265239066489067 | 0.004600035026669502 | pass |
| intfloat/multilingual-e5-large | no_rerank | 40 | completed | 0.4464064852755051 | 0.6569880952380952 | 0.5384313510563511 | 0.004399975296109915 | pass |
| bkai-foundation-models/vietnamese-bi-encoder | no_rerank | 40 | completed | 0.28013839245905015 | 0.4382208994708995 | 0.369621225996226 | 0.0036050245398655547 | pass |
| dangvantuan/vietnamese-embedding | no_rerank | 40 | completed | 0.1722914029139554 | 0.28552248677248676 | 0.24019670607170607 | 0.003805028973147274 | pass |
| contextboxai/halong_embedding | no_rerank | 40 | completed | 0.403114312416789 | 0.5955529100529101 | 0.5168065684315684 | 0.005005035200156272 | pass |
| BAAI/bge-m3 | cross-encoder/ms-marco-MiniLM-L-6-v2 | 40 | completed | 0.3197689182072641 | 0.4680449735449736 | 0.5265239066489067 | 133.28863000206186 | pass |
| intfloat/multilingual-e5-large | cross-encoder/ms-marco-MiniLM-L-6-v2 | 40 | completed | 0.32905702879294685 | 0.48167989417989415 | 0.5384313510563511 | 139.52317994844634 | pass |
| bkai-foundation-models/vietnamese-bi-encoder | cross-encoder/ms-marco-MiniLM-L-6-v2 | 40 | completed | 0.2691960761192982 | 0.4242222222222222 | 0.369621225996226 | 135.3280599694699 | pass |
| dangvantuan/vietnamese-embedding | cross-encoder/ms-marco-MiniLM-L-6-v2 | 40 | completed | 0.22176303821706678 | 0.377484126984127 | 0.24019670607170607 | 136.3475600053789 | pass |
| contextboxai/halong_embedding | cross-encoder/ms-marco-MiniLM-L-6-v2 | 40 | completed | 0.3149872752279791 | 0.4776917989417989 | 0.5168065684315684 | 138.93090498168021 | pass |
| BAAI/bge-m3 | BAAI/bge-reranker-base | 40 | completed | 0.40979541583298995 | 0.5992460317460317 | 0.5265239066489067 | 527.5006250187289 | pass |
| intfloat/multilingual-e5-large | BAAI/bge-reranker-base | 40 | completed | 0.41476993697361825 | 0.6017910052910053 | 0.5384313510563511 | 513.0161950102774 | pass |
| bkai-foundation-models/vietnamese-bi-encoder | BAAI/bge-reranker-base | 40 | completed | 0.3405031711476738 | 0.5252526455026455 | 0.369621225996226 | 506.7647349991604 | pass |
| dangvantuan/vietnamese-embedding | BAAI/bge-reranker-base | 40 | completed | 0.26530772510909006 | 0.43688095238095237 | 0.24019670607170607 | 507.47265002573846 | pass |
| contextboxai/halong_embedding | BAAI/bge-reranker-base | 40 | completed | 0.41573912894900783 | 0.6029126984126983 | 0.5168065684315684 | 504.8311999969883 | pass |
| BAAI/bge-m3 | BAAI/bge-reranker-v2-m3 | 40 | completed | 0.5057694907366248 | 0.7364021164021164 | 0.5265239066489067 | 1675.9207899856847 | reject |
| intfloat/multilingual-e5-large | BAAI/bge-reranker-v2-m3 | 40 | completed | 0.5091502591405336 | 0.7345026455026455 | 0.5384313510563511 | 1693.3968399825972 | reject |
| bkai-foundation-models/vietnamese-bi-encoder | BAAI/bge-reranker-v2-m3 | 40 | completed | 0.41480772526452003 | 0.6471362433862434 | 0.369621225996226 | 1676.7147150065284 | reject |
| dangvantuan/vietnamese-embedding | BAAI/bge-reranker-v2-m3 | 40 | completed | 0.3067201952042145 | 0.526957671957672 | 0.24019670607170607 | 1659.995754971169 | reject |
| contextboxai/halong_embedding | BAAI/bge-reranker-v2-m3 | 40 | completed | 0.4974346990557529 | 0.7268412698412698 | 0.5168065684315684 | 1690.4943749628728 | reject |
| BAAI/bge-m3 | jinaai/jina-reranker-v2-base-multilingual | 40 | completed | 0.5030111124878042 | 0.7395965608465609 | 0.5265239066489067 | 176.99253997416236 | pass |
| intfloat/multilingual-e5-large | jinaai/jina-reranker-v2-base-multilingual | 40 | completed | 0.5039126419471386 | 0.734989417989418 | 0.5384313510563511 | 177.0335749752121 | pass |
| bkai-foundation-models/vietnamese-bi-encoder | jinaai/jina-reranker-v2-base-multilingual | 40 | completed | 0.412866722272962 | 0.6478227513227514 | 0.369621225996226 | 173.2844899961492 | pass |
| dangvantuan/vietnamese-embedding | jinaai/jina-reranker-v2-base-multilingual | 40 | completed | 0.31043758425615975 | 0.5397222222222222 | 0.24019670607170607 | 172.74722000584006 | pass |
| contextboxai/halong_embedding | jinaai/jina-reranker-v2-base-multilingual | 40 | completed | 0.4952747954759219 | 0.7299246031746032 | 0.5168065684315684 | 175.62550999282394 | pass |
| BAAI/bge-m3 | namdp-ptit/ViRanker | 40 | completed | 0.47807395540490527 | 0.699978835978836 | 0.5265239066489067 | 1656.9521799916402 | reject |
| intfloat/multilingual-e5-large | namdp-ptit/ViRanker | 40 | completed | 0.48242422140692487 | 0.6959404761904762 | 0.5384313510563511 | 1643.1711250304943 | reject |
| bkai-foundation-models/vietnamese-bi-encoder | namdp-ptit/ViRanker | 40 | completed | 0.4006236599802864 | 0.623271164021164 | 0.369621225996226 | 1624.8550650430843 | reject |
| dangvantuan/vietnamese-embedding | namdp-ptit/ViRanker | 40 | completed | 0.2957668043368237 | 0.5022063492063492 | 0.24019670607170607 | 1627.4521250015825 | reject |
| contextboxai/halong_embedding | namdp-ptit/ViRanker | 40 | completed | 0.4759917553919594 | 0.6876772486772487 | 0.5168065684315684 | 1635.0044349848758 | reject |

## Config

- Dataset: `phase4_reranker_final_slide_v1`
- Strategy: `recursive`
