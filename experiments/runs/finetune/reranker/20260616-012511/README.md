---
tags:
- sentence-transformers
- cross-encoder
- reranker
- generated_from_trainer
- dataset_size:75606
- loss:BinaryCrossEntropyLoss
base_model: jinaai/jina-reranker-v2-base-multilingual
pipeline_tag: text-ranking
library_name: sentence-transformers
metrics:
- map
- mrr@10
- ndcg@10
model-index:
- name: CrossEncoder based on jinaai/jina-reranker-v2-base-multilingual
  results:
  - task:
      type: cross-encoder-reranking
      name: Cross Encoder Reranking
    dataset:
      name: val rerank
      type: val_rerank
    metrics:
    - type: map
      value: 0.8376942355889725
      name: Map
    - type: mrr@10
      value: 0.8376942355889725
      name: Mrr@10
    - type: ndcg@10
      value: 0.8791567343379376
      name: Ndcg@10
---

# CrossEncoder based on jinaai/jina-reranker-v2-base-multilingual

This is a [Cross Encoder](https://www.sbert.net/docs/cross_encoder/usage/usage.html) model finetuned from [jinaai/jina-reranker-v2-base-multilingual](https://huggingface.co/jinaai/jina-reranker-v2-base-multilingual) using the [sentence-transformers](https://www.SBERT.net) library. It computes scores for pairs of texts, which can be used for text reranking and semantic search.

## Model Details

### Model Description
- **Model Type:** Cross Encoder
- **Base model:** [jinaai/jina-reranker-v2-base-multilingual](https://huggingface.co/jinaai/jina-reranker-v2-base-multilingual) <!-- at revision 9cfeff2df7d40d1b78e75e5e9cebec92a99813c9 -->
- **Maximum Sequence Length:** 384 tokens
- **Number of Output Labels:** 1 label
<!-- - **Training Dataset:** Unknown -->
<!-- - **Language:** Unknown -->
<!-- - **License:** Unknown -->

### Model Sources

- **Documentation:** [Sentence Transformers Documentation](https://sbert.net)
- **Documentation:** [Cross Encoder Documentation](https://www.sbert.net/docs/cross_encoder/usage/usage.html)
- **Repository:** [Sentence Transformers on GitHub](https://github.com/huggingface/sentence-transformers)
- **Hugging Face:** [Cross Encoders on Hugging Face](https://huggingface.co/models?library=sentence-transformers&other=cross-encoder)

## Usage

### Direct Usage (Sentence Transformers)

First install the Sentence Transformers library:

```bash
pip install -U sentence-transformers
```

Then you can load this model and run inference.
```python
from sentence_transformers import CrossEncoder

# Download from the 🤗 Hub
model = CrossEncoder("cross_encoder_model_id")
# Get scores for pairs of texts
pairs = [
    ['Có cách nào đơn giản hơn để tính loss không?', 'để cho cái loss của mình là nhỏ nhất thì nó có một cái thuộc toán là gọi là thuộc toán Lan truyền ngược hay còn gọi là Back propagation vấn đề đó là khi chúng ta đã có loss rồi, tức là cái size số rồi thì làm sao để cập nhật cái trọng số nữa tiếp theo để cho cái việc cập nhật trọng số này nó sẽ có xu hướng khiến cho cái loss của mình là đi xuống Tại vì hồi nãy chúng ta có một nguyên tắc đó là loss mà càng nhỏ là càng tốt Thực toán của chúng ta là lang truyền ngược Nhưng mà trước khi để thực hiện được thực toán lang truyền ngược thì chúng ta sẽ phải thực hiện thực toán feedforward process là chúng ta sẽ lang truyền theo chiều thuận chúng ta lang truyền theo chiều thuận sau đó đến được giá'],
    ['Keras giúp tiết kiệm công sức như thế nào trong việc tính đạo hàm?', 'Chúng ta sẽ cài đặt thục bán LiniRech. Chúng ta sẽ cài bằng 3 phiên bản. Đó là chúng ta sẽ dùng tham số theta như là những biến rời này. Theta0, theta1 ở đây. Trong các phiên bản dạng vector hóa, chúng ta sẽ gom tất cả tham số theta 0, theta 1 vào chung một cái biến, đó là theta. Vì việc này sẽ giúp cho chương trình của mình nhìn gọn hơn. Và phiên bản số 3, đó là chúng ta sẽ sử dụng thư viện Keras. Thì cái phiên bản kài đặt sử dụng thư viện Keras sẽ giúp cho chúng ta tiết kiệm được rất nhiều công sức trong việc tính đạo hàm. Chúng ta sẽ không cần phải ngồi tính toán các giá trị đạo hàm một cách tường minh mà Keras sẽ tự tính toán và tự tính đạo hàm này cho chúng ta luôn'],
    ['Tại sao tính toán trọng số lại tốn chi phí?', '. Tuy nhiên, đâu đó nó vẫn sẽ có một điểm yếu đó chính là chúng ta sẽ phải tính trọng số này. làm sao chúng ta có được cái trọng số này một cách phù hợp và trong nhiều tình huống nếu như chúng ta sử dụng cái độ chính xác trên tập train hoặc tập validation này thì đâu đó nó sẽ tốn chi phí để tính toán rồi nó sẽ tốn chi phí tính toán ra các cái bộ trọng số này thì đó chính là 3 cái kỹ thuật chính nhất cho hướng tiếp cận là các phương pháp ensemble cơ bản bao gồm là Voting, trung bình và trung bình trọng số, Weighted Averaging.'],
    ['Boosting cải thiện model như thế nào qua các iterations?', 'N và chúng ta sẽ train cái model thứ N và N cái model này sẽ được tổng hợp lại với một cái kỹ thuật ensemble thì ensemble này có thể là những kỹ thuật cơ bản như là voting averaging hoặc bản thân cái phương pháp ensemble này nó được xuất phát từ cái thuật toán của mình tức là cái thuật toán kết hợp giữa Model số 1 Model số 2 Model số 3 với những cái trọng số mà mô hình của mình nó đã được học trong cái quá trình boosting thì để hiểu rõ hơn về kỹ thuật Boosting thì chúng ta sẽ lấy một cái thuật toán đại diện đó chính là thuật toán Gradient Boost và Gradient Boost ý tưởng của nó đó là nó sẽ xây dựng một cái chuỗi một cái chuỗi các cái cây quyết định liên tiếp với nhau thì nếu như bagging nó'],
    ['Vector biểu diễn có ảnh hưởng gì đến model performance?', 'diễn của ảnh Rồi, còn ở đây sẽ là cái vector biểu diễn của văn bản Và ở đây chúng ta thấy trong cái sơ đồ này chúng ta thấy có cái module cross-attention nhưng mà được làm mờ và gạch sọc đi thì hàm ý đó là chúng ta sẽ không có sự tương tác giữa hình ảnh với văn bản là hàm ý đó là để cho hai cái loại đặc trưng này độc lập nhau để sau này khi chúng ta huấn luyện cái mô hình này xong thì chúng ta có thể sử dụng hai cái module này như là hai cái embedding module cho hình ảnh riêng và cho văn bản riêng tức là chúng ta sẽ cho hình ảnh vào và nó sẽ ra vector biểu diễn nó không cần có sự can thiệp của một cái module văn bản nào khác và ngược lại chúng ta có thể đưa văn bản vào nó sẽ ra cái vector'],
]
scores = model.predict(pairs)
print(scores.shape)
# (5,)

# Or rank different texts based on similarity to a single text
ranks = model.rank(
    'Có cách nào đơn giản hơn để tính loss không?',
    [
        'để cho cái loss của mình là nhỏ nhất thì nó có một cái thuộc toán là gọi là thuộc toán Lan truyền ngược hay còn gọi là Back propagation vấn đề đó là khi chúng ta đã có loss rồi, tức là cái size số rồi thì làm sao để cập nhật cái trọng số nữa tiếp theo để cho cái việc cập nhật trọng số này nó sẽ có xu hướng khiến cho cái loss của mình là đi xuống Tại vì hồi nãy chúng ta có một nguyên tắc đó là loss mà càng nhỏ là càng tốt Thực toán của chúng ta là lang truyền ngược Nhưng mà trước khi để thực hiện được thực toán lang truyền ngược thì chúng ta sẽ phải thực hiện thực toán feedforward process là chúng ta sẽ lang truyền theo chiều thuận chúng ta lang truyền theo chiều thuận sau đó đến được giá',
        'Chúng ta sẽ cài đặt thục bán LiniRech. Chúng ta sẽ cài bằng 3 phiên bản. Đó là chúng ta sẽ dùng tham số theta như là những biến rời này. Theta0, theta1 ở đây. Trong các phiên bản dạng vector hóa, chúng ta sẽ gom tất cả tham số theta 0, theta 1 vào chung một cái biến, đó là theta. Vì việc này sẽ giúp cho chương trình của mình nhìn gọn hơn. Và phiên bản số 3, đó là chúng ta sẽ sử dụng thư viện Keras. Thì cái phiên bản kài đặt sử dụng thư viện Keras sẽ giúp cho chúng ta tiết kiệm được rất nhiều công sức trong việc tính đạo hàm. Chúng ta sẽ không cần phải ngồi tính toán các giá trị đạo hàm một cách tường minh mà Keras sẽ tự tính toán và tự tính đạo hàm này cho chúng ta luôn',
        '. Tuy nhiên, đâu đó nó vẫn sẽ có một điểm yếu đó chính là chúng ta sẽ phải tính trọng số này. làm sao chúng ta có được cái trọng số này một cách phù hợp và trong nhiều tình huống nếu như chúng ta sử dụng cái độ chính xác trên tập train hoặc tập validation này thì đâu đó nó sẽ tốn chi phí để tính toán rồi nó sẽ tốn chi phí tính toán ra các cái bộ trọng số này thì đó chính là 3 cái kỹ thuật chính nhất cho hướng tiếp cận là các phương pháp ensemble cơ bản bao gồm là Voting, trung bình và trung bình trọng số, Weighted Averaging.',
        'N và chúng ta sẽ train cái model thứ N và N cái model này sẽ được tổng hợp lại với một cái kỹ thuật ensemble thì ensemble này có thể là những kỹ thuật cơ bản như là voting averaging hoặc bản thân cái phương pháp ensemble này nó được xuất phát từ cái thuật toán của mình tức là cái thuật toán kết hợp giữa Model số 1 Model số 2 Model số 3 với những cái trọng số mà mô hình của mình nó đã được học trong cái quá trình boosting thì để hiểu rõ hơn về kỹ thuật Boosting thì chúng ta sẽ lấy một cái thuật toán đại diện đó chính là thuật toán Gradient Boost và Gradient Boost ý tưởng của nó đó là nó sẽ xây dựng một cái chuỗi một cái chuỗi các cái cây quyết định liên tiếp với nhau thì nếu như bagging nó',
        'diễn của ảnh Rồi, còn ở đây sẽ là cái vector biểu diễn của văn bản Và ở đây chúng ta thấy trong cái sơ đồ này chúng ta thấy có cái module cross-attention nhưng mà được làm mờ và gạch sọc đi thì hàm ý đó là chúng ta sẽ không có sự tương tác giữa hình ảnh với văn bản là hàm ý đó là để cho hai cái loại đặc trưng này độc lập nhau để sau này khi chúng ta huấn luyện cái mô hình này xong thì chúng ta có thể sử dụng hai cái module này như là hai cái embedding module cho hình ảnh riêng và cho văn bản riêng tức là chúng ta sẽ cho hình ảnh vào và nó sẽ ra vector biểu diễn nó không cần có sự can thiệp của một cái module văn bản nào khác và ngược lại chúng ta có thể đưa văn bản vào nó sẽ ra cái vector',
    ]
)
# [{'corpus_id': ..., 'score': ...}, {'corpus_id': ..., 'score': ...}, ...]
```

<!--
### Direct Usage (Transformers)

<details><summary>Click to see the direct usage in Transformers</summary>

</details>
-->

<!--
### Downstream Usage (Sentence Transformers)

You can finetune this model on your own dataset.

<details><summary>Click to expand</summary>

</details>
-->

<!--
### Out-of-Scope Use

*List how the model may foreseeably be misused and address what users ought not to do with the model.*
-->

## Evaluation

### Metrics

#### Cross Encoder Reranking

* Dataset: `val_rerank`
* Evaluated with [<code>CrossEncoderRerankingEvaluator</code>](https://sbert.net/docs/package_reference/cross_encoder/evaluation.html#sentence_transformers.cross_encoder.evaluation.CrossEncoderRerankingEvaluator) with these parameters:
  ```json
  {
      "at_k": 10
  }
  ```

| Metric      | Value      |
|:------------|:-----------|
| map         | 0.8377     |
| mrr@10      | 0.8377     |
| **ndcg@10** | **0.8792** |

<!--
## Bias, Risks and Limitations

*What are the known or foreseeable issues stemming from this model? You could also flag here known failure cases or weaknesses of the model.*
-->

<!--
### Recommendations

*What are recommendations with respect to the foreseeable issues? For example, filtering explicit content.*
-->

## Training Details

### Training Dataset

#### Unnamed Dataset

* Size: 75,606 training samples
* Columns: <code>sentence_0</code>, <code>sentence_1</code>, and <code>label</code>
* Approximate statistics based on the first 1000 samples:
  |         | sentence_0                                                                                     | sentence_1                                                                                       | label                                                          |
  |:--------|:-----------------------------------------------------------------------------------------------|:-------------------------------------------------------------------------------------------------|:---------------------------------------------------------------|
  | type    | string                                                                                         | string                                                                                           | float                                                          |
  | details | <ul><li>min: 33 characters</li><li>mean: 57.27 characters</li><li>max: 93 characters</li></ul> | <ul><li>min: 42 characters</li><li>mean: 619.84 characters</li><li>max: 700 characters</li></ul> | <ul><li>min: 0.0</li><li>mean: 0.18</li><li>max: 1.0</li></ul> |
* Samples:
  | sentence_0                                                                      | sentence_1                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | label            |
  |:--------------------------------------------------------------------------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:-----------------|
  | <code>Có cách nào đơn giản hơn để tính loss không?</code>                       | <code>để cho cái loss của mình là nhỏ nhất thì nó có một cái thuộc toán là gọi là thuộc toán Lan truyền ngược hay còn gọi là Back propagation vấn đề đó là khi chúng ta đã có loss rồi, tức là cái size số rồi thì làm sao để cập nhật cái trọng số nữa tiếp theo để cho cái việc cập nhật trọng số này nó sẽ có xu hướng khiến cho cái loss của mình là đi xuống Tại vì hồi nãy chúng ta có một nguyên tắc đó là loss mà càng nhỏ là càng tốt Thực toán của chúng ta là lang truyền ngược Nhưng mà trước khi để thực hiện được thực toán lang truyền ngược thì chúng ta sẽ phải thực hiện thực toán feedforward process là chúng ta sẽ lang truyền theo chiều thuận chúng ta lang truyền theo chiều thuận sau đó đến được giá</code> | <code>0.0</code> |
  | <code>Keras giúp tiết kiệm công sức như thế nào trong việc tính đạo hàm?</code> | <code>Chúng ta sẽ cài đặt thục bán LiniRech. Chúng ta sẽ cài bằng 3 phiên bản. Đó là chúng ta sẽ dùng tham số theta như là những biến rời này. Theta0, theta1 ở đây. Trong các phiên bản dạng vector hóa, chúng ta sẽ gom tất cả tham số theta 0, theta 1 vào chung một cái biến, đó là theta. Vì việc này sẽ giúp cho chương trình của mình nhìn gọn hơn. Và phiên bản số 3, đó là chúng ta sẽ sử dụng thư viện Keras. Thì cái phiên bản kài đặt sử dụng thư viện Keras sẽ giúp cho chúng ta tiết kiệm được rất nhiều công sức trong việc tính đạo hàm. Chúng ta sẽ không cần phải ngồi tính toán các giá trị đạo hàm một cách tường minh mà Keras sẽ tự tính toán và tự tính đạo hàm này cho chúng ta luôn</code>                   | <code>1.0</code> |
  | <code>Tại sao tính toán trọng số lại tốn chi phí?</code>                        | <code>. Tuy nhiên, đâu đó nó vẫn sẽ có một điểm yếu đó chính là chúng ta sẽ phải tính trọng số này. làm sao chúng ta có được cái trọng số này một cách phù hợp và trong nhiều tình huống nếu như chúng ta sử dụng cái độ chính xác trên tập train hoặc tập validation này thì đâu đó nó sẽ tốn chi phí để tính toán rồi nó sẽ tốn chi phí tính toán ra các cái bộ trọng số này thì đó chính là 3 cái kỹ thuật chính nhất cho hướng tiếp cận là các phương pháp ensemble cơ bản bao gồm là Voting, trung bình và trung bình trọng số, Weighted Averaging.</code>                                                                                                                                                                       | <code>1.0</code> |
* Loss: [<code>BinaryCrossEntropyLoss</code>](https://sbert.net/docs/package_reference/cross_encoder/losses.html#binarycrossentropyloss) with these parameters:
  ```json
  {
      "activation_fn": "torch.nn.modules.linear.Identity",
      "pos_weight": null
  }
  ```

### Training Hyperparameters
#### Non-Default Hyperparameters

- `eval_strategy`: steps
- `num_train_epochs`: 1

#### All Hyperparameters
<details><summary>Click to expand</summary>

- `overwrite_output_dir`: False
- `do_predict`: False
- `eval_strategy`: steps
- `prediction_loss_only`: True
- `per_device_train_batch_size`: 8
- `per_device_eval_batch_size`: 8
- `per_gpu_train_batch_size`: None
- `per_gpu_eval_batch_size`: None
- `gradient_accumulation_steps`: 1
- `eval_accumulation_steps`: None
- `torch_empty_cache_steps`: None
- `learning_rate`: 5e-05
- `weight_decay`: 0.0
- `adam_beta1`: 0.9
- `adam_beta2`: 0.999
- `adam_epsilon`: 1e-08
- `max_grad_norm`: 1
- `num_train_epochs`: 1
- `max_steps`: -1
- `lr_scheduler_type`: linear
- `lr_scheduler_kwargs`: {}
- `warmup_ratio`: 0.0
- `warmup_steps`: 0
- `log_level`: passive
- `log_level_replica`: warning
- `log_on_each_node`: True
- `logging_nan_inf_filter`: True
- `save_safetensors`: True
- `save_on_each_node`: False
- `save_only_model`: False
- `restore_callback_states_from_checkpoint`: False
- `no_cuda`: False
- `use_cpu`: False
- `use_mps_device`: False
- `seed`: 42
- `data_seed`: None
- `jit_mode_eval`: False
- `bf16`: False
- `fp16`: False
- `fp16_opt_level`: O1
- `half_precision_backend`: auto
- `bf16_full_eval`: False
- `fp16_full_eval`: False
- `tf32`: None
- `local_rank`: 0
- `ddp_backend`: None
- `tpu_num_cores`: None
- `tpu_metrics_debug`: False
- `debug`: []
- `dataloader_drop_last`: False
- `dataloader_num_workers`: 0
- `dataloader_prefetch_factor`: None
- `past_index`: -1
- `disable_tqdm`: False
- `remove_unused_columns`: True
- `label_names`: None
- `load_best_model_at_end`: False
- `ignore_data_skip`: False
- `fsdp`: []
- `fsdp_min_num_params`: 0
- `fsdp_config`: {'min_num_params': 0, 'xla': False, 'xla_fsdp_v2': False, 'xla_fsdp_grad_ckpt': False}
- `fsdp_transformer_layer_cls_to_wrap`: None
- `accelerator_config`: {'split_batches': False, 'dispatch_batches': None, 'even_batches': True, 'use_seedable_sampler': True, 'non_blocking': False, 'gradient_accumulation_kwargs': None}
- `parallelism_config`: None
- `deepspeed`: None
- `label_smoothing_factor`: 0.0
- `optim`: adamw_torch_fused
- `optim_args`: None
- `adafactor`: False
- `group_by_length`: False
- `length_column_name`: length
- `project`: huggingface
- `trackio_space_id`: trackio
- `ddp_find_unused_parameters`: None
- `ddp_bucket_cap_mb`: None
- `ddp_broadcast_buffers`: False
- `dataloader_pin_memory`: True
- `dataloader_persistent_workers`: False
- `skip_memory_metrics`: True
- `use_legacy_prediction_loop`: False
- `push_to_hub`: False
- `resume_from_checkpoint`: None
- `hub_model_id`: None
- `hub_strategy`: every_save
- `hub_private_repo`: None
- `hub_always_push`: False
- `hub_revision`: None
- `gradient_checkpointing`: False
- `gradient_checkpointing_kwargs`: None
- `include_inputs_for_metrics`: False
- `include_for_metrics`: []
- `eval_do_concat_batches`: True
- `fp16_backend`: auto
- `push_to_hub_model_id`: None
- `push_to_hub_organization`: None
- `mp_parameters`: 
- `auto_find_batch_size`: False
- `full_determinism`: False
- `torchdynamo`: None
- `ray_scope`: last
- `ddp_timeout`: 1800
- `torch_compile`: False
- `torch_compile_backend`: None
- `torch_compile_mode`: None
- `include_tokens_per_second`: False
- `include_num_input_tokens_seen`: no
- `neftune_noise_alpha`: None
- `optim_target_modules`: None
- `batch_eval_metrics`: False
- `eval_on_start`: False
- `use_liger_kernel`: False
- `liger_kernel_config`: None
- `eval_use_gather_object`: False
- `average_tokens_across_devices`: True
- `prompts`: None
- `batch_sampler`: batch_sampler
- `multi_dataset_batch_sampler`: proportional
- `router_mapping`: {}
- `learning_rate_mapping`: {}

</details>

### Training Logs
| Epoch  | Step | Training Loss | val_rerank_ndcg@10 |
|:------:|:----:|:-------------:|:------------------:|
| 0.0529 | 500  | 0.4701        | 0.7899             |
| 0.1058 | 1000 | 0.3793        | 0.8285             |
| 0.1587 | 1500 | 0.3445        | 0.8587             |
| 0.2116 | 2000 | 0.34          | 0.8659             |
| 0.2645 | 2500 | 0.3298        | 0.8730             |
| 0.3174 | 3000 | 0.3301        | 0.8705             |
| 0.3703 | 3500 | 0.3212        | 0.8733             |
| 0.4232 | 4000 | 0.3048        | 0.8770             |
| 0.4761 | 4500 | 0.3042        | 0.8725             |
| 0.5290 | 5000 | 0.3126        | 0.8766             |
| 0.5819 | 5500 | 0.3128        | 0.8758             |
| 0.6349 | 6000 | 0.3086        | 0.8766             |
| 0.6878 | 6500 | 0.2989        | 0.8779             |
| 0.7407 | 7000 | 0.313         | 0.8787             |
| 0.7936 | 7500 | 0.2985        | 0.8775             |
| 0.8465 | 8000 | 0.2875        | 0.8792             |


### Framework Versions
- Python: 3.12.9
- Sentence Transformers: 5.1.2
- Transformers: 4.57.1
- PyTorch: 2.10.0+cu128
- Accelerate: 1.10.1
- Datasets: 4.3.0
- Tokenizers: 0.22.1

## Citation

### BibTeX

#### Sentence Transformers
```bibtex
@inproceedings{reimers-2019-sentence-bert,
    title = "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks",
    author = "Reimers, Nils and Gurevych, Iryna",
    booktitle = "Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing",
    month = "11",
    year = "2019",
    publisher = "Association for Computational Linguistics",
    url = "https://arxiv.org/abs/1908.10084",
}
```

<!--
## Glossary

*Clearly define terms in order to be accessible across audiences.*
-->

<!--
## Model Card Authors

*Lists the people who create the model card, providing recognition and accountability for the detailed work that goes into its construction.*
-->

<!--
## Model Card Contact

*Provides a way for people who have updates to the Model Card, suggestions, or questions, to contact the Model Card authors.*
-->