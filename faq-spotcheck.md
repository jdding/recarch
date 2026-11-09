# FAQ 抽查表

共 30 条，随机抽自全部自动生成的问答，种子固定，重跑结果不变。每条都是模板拼接卡片字段，答案里的数字已经机器核对过。
请看三件事：答案是否忠实于卡片，读起来是否自然，有没有把未报告说成已报告。
确认没问题后，把对应 data/faq/<id>.yaml 的 reviewed 改成 true，卡片页才会显示问答。

## 1. meta-andromeda-2024 / online

- 英文问：Does Meta Andromeda have online evidence, and how long was the A/B?
- 英文答：Online evidence: Online numbers. A/B duration: not reported. A/B traffic: not reported.
- 中文问：Meta Andromeda 有线上证据吗，A/B 做了多久？
- 中文答：线上证据：有线上数据。A/B 时长：未报告。A/B 流量：未报告。
- 引用字段：deployment.online_evidence, deployment.ab_duration, deployment.ab_traffic
- 抽查结论：[ ] 通过  [ ] 有问题

## 2. jd-gcrank-2026 / results

- 英文问：What results does GCRank report?
- 英文答：Online 7-day A/B with a 20% traffic allocation against the production DLRM, all p < 0.0001: CTR +5.07%, CVR +4.71%, RPM +6.42%, with TP99 latency up about 2 ms; daily gains stay stable across the 7 days, and the model was then rolled out to all platform traffic. Offline AUC on the industrial set is 0.7679 for CTR and 0.7053 for CVR for GCRank against 0.7513 and 0.6619 for the production DLRM and 0.7545 and 0.6659 for HSTU.
- 中文问：GCRank 报告了哪些结果？
- 中文答：线上 7 天 A/B，分配 20% 流量，对比线上 DLRM，全部 p < 0.0001：CTR +5.07%，CVR +4.71%，RPM +6.42%，TP99 延迟增加约 2 ms；7 天内每日收益保持稳定，随后模型推到平台全量流量。工业数据集上的离线 AUC：GCRank 的 CTR 为 0.7679，CVR 为 0.7053；线上 DLRM 分别为 0.7513 和 0.6619；HSTU 分别为 0.7545 和 0.6659。
- 引用字段：results_reported
- 抽查结论：[ ] 通过  [ ] 有问题

## 3. tencent-lfm4ads-2025 / core

- 英文问：What is the core idea of LFM4Ads?
- 英文答：Transfer all three representations from a large ads foundation model into downstream tasks at feature, module and model level.
- 中文问：LFM4Ads 的核心思路是什么？
- 中文答：把大型广告基础模型的三类表示按特征、模块和模型三个层级迁移进下游任务。
- 引用字段：core_idea
- 抽查结论：[ ] 通过  [ ] 有问题

## 4. doordash-homepage-2022 / caveats

- 英文问：What should I keep in mind when reading the results of DoorDash homepage ranking?
- 英文答：2022 post; DoorDash has since published newer LLM-assisted personalization posts not covered here.
- 中文问：读 DoorDash homepage ranking 的结果时要注意什么？
- 中文答：这是 2022 年的文章；此后 DoorDash 又发布了较新的由 LLM 辅助的个性化文章，这里没有涵盖。
- 引用字段：caveats.0
- 抽查结论：[ ] 通过  [ ] 有问题

## 5. facebook-search-ebr-2020 / what

- 英文问：What is Embedding-based Retrieval in Facebook Search, in one sentence?
- 英文答：Facebook Search retrieves with a unified two-tower embedding that matches searcher, query and context against the document, trained with triplet loss and hard negatives.
- 中文问：Embedding-based Retrieval in Facebook Search 一句话是什么？
- 中文答：Facebook 搜索 用统一的双塔 embedding 做召回，把搜索者、query 和上下文与文档匹配，用 triplet 损失和 hard 负样本训练。
- 引用字段：tldr
- 抽查结论：[ ] 通过  [ ] 有问题

## 6. bytedance-mixformer-2026 / results

- 英文问：What results does MixFormer report?
- 英文答：Offline (Table 1, relative to TA to DLRM baseline AUC 0.8554 Finish / 0.8124 Skip): MixFormer-medium +1.28% Finish AUC, +1.60% Finish UAUC, +1.60% Skip AUC, +2.46% Skip UAUC with 1,226M dense params and 3,503 GFLOPs/batch; STCA to RankMixer +1.12% / +1.40% / +1.43% / +2.14% with 1,255M and 6,736 GFLOPs; UI-MixFormer-medium has the same accuracy at 2,242 GFLOPs (about 36% fewer FLOPs). Online A/B for two weeks vs the deployed STCA to RankMixer baseline per Table 2: Douyin overall Active Day +0.0415%, Duration +0.2799%, Like +0.1766%, Finish +0.3897%, Comment +0.7035%; Douyin Lite overall Active Day +0.0252%, Duration +0.4105%, Like +0.2125%, Finish +0.2924%, Comment +1.9097%. Paper states all are significant and not yet converged.
- 中文问：MixFormer 报告了哪些结果？
- 中文答：离线见表 1，相对 TA to DLRM 基线，基线的 AUC 为 Finish 0.8554、Skip 0.8124：MixFormer-medium 的 Finish AUC +1.28%，Finish UAUC +1.60%，Skip AUC +1.60%，Skip UAUC +2.46%，稠密参数 1,226M，每个 batch 3,503 GFLOPs；STCA to RankMixer 为 +1.12%、+1.40%、+1.43%、+2.14%，参数 1,255M，6,736 GFLOPs；UI-MixFormer-medium 精度相同，只需 2,242 GFLOPs，FLOPs 约减少 36%。两周线上 A/B，对比线上的 STCA to RankMixer 基线，见表 2：抖音整体活跃天数 +0.0415%，时长 +0.2799%，点赞 +0.1766%，完播 +0.3897%，评论 +0.7035%；抖音极速版整体活跃天数 +0.0252%，时长 +0.4105%，点赞 +0.2125%，完播 +0.2924%，评论 +1.9097%。论文称所有指标都显著，且尚未收敛。
- 引用字段：results_reported
- 抽查结论：[ ] 通过  [ ] 有问题

## 7. alibaba-hisac-2026 / caveats

- 英文问：What should I keep in mind when reading the results of HiSAC?
- 英文答：The online baseline is described only as the strongest prior compression method in production; the paper does not name it. The paper reports no traffic share, bucket counts or user counts for the two-week A/B test.
- 中文问：读 HiSAC 的结果时要注意什么？
- 中文答：线上基线只被描述为线上最强前代压缩方法，论文未给名字。 论文未报告两周 A/B 的流量占比、分桶数或用户数。
- 引用字段：caveats.0, caveats.1
- 抽查结论：[ ] 通过  [ ] 有问题

## 8. meituan-mtgr-2025 / what

- 英文问：What is MTGR, in one sentence?
- 英文答：HSTU-based generative ranker that keeps DLRM cross features; vs a years-optimized DLRM, conversion volume +1.22% and CTR +1.31% with 12% cheaper inference.
- 中文问：MTGR 一句话是什么？
- 中文答：基于 HSTU 的生成式排序器，保留 DLRM 的交叉特征；对比优化多年的 DLRM，转化量 +1.22%，CTR +1.31%，推理成本降低 12%。
- 引用字段：tldr
- 抽查结论：[ ] 通过  [ ] 有问题

## 9. alibaba-degre-2026 / caveats

- 英文问：What should I keep in mind when reading the results of DeGRe?
- 英文答：The online control is a base point-wise strategy, and the only generative or list-wise online baseline is PRM, a discriminative reranker; no other generative reranker was tested online. Offline hit rate is measured by a learned external evaluator on sampled permutations, so it is a model-based proxy, not logged user behavior.
- 中文问：读 DeGRe 的结果时要注意什么？
- 中文答：线上对照组是基础 point-wise 策略，而线上唯一的生成式或 list-wise 基线是判别式重排模型 PRM；没有在线上测试其他生成式重排模型。 离线命中率由一个学习得到的外部评估器在采样排列上测得，因此是基于模型的代理指标，不是真实的用户行为日志。
- 引用字段：caveats.0, caveats.1
- 抽查结论：[ ] 通过  [ ] 有问题

## 10. related-pins-pinterest-2017 / online

- 英文问：Does Related Pins at Pinterest have online evidence, and how long was the A/B?
- 英文答：Online evidence: Online numbers. A/B duration: not reported. A/B traffic: not reported.
- 中文问：Related Pins at Pinterest 有线上证据吗，A/B 做了多久？
- 中文答：线上证据：有线上数据。A/B 时长：未报告。A/B 流量：未报告。
- 引用字段：deployment.online_evidence, deployment.ab_duration, deployment.ab_traffic
- 抽查结论：[ ] 通过  [ ] 有问题

## 11. sim-alibaba-2020 / who

- 英文问：Who built SIM and where does it run?
- 英文答：SIM comes from Alibaba, 2020. Deployed in: Alibaba display advertising CTR prediction since 2019, serving the main traffic.
- 中文问：SIM 是谁做的，用在哪里？
- 中文答：SIM 来自 阿里巴巴，2020 年。上线位置：自 2019 年起用于阿里巴巴展示广告的 CTR 预测，承接主流量。
- 引用字段：company, year, deployed_in
- 抽查结论：[ ] 通过  [ ] 有问题

## 12. meta-rankgraph2-2026 / code

- 英文问：Is there code for RankGraph-2?
- 英文答：Code status: No code found.
- 中文问：RankGraph-2 有代码吗？
- 中文答：代码状态：未发现公开代码。
- 引用字段：code.status
- 抽查结论：[ ] 通过  [ ] 有问题

## 13. youtube-dnn-2016 / online

- 英文问：Does Deep Neural Networks for YouTube Recommendations have online evidence, and how long was the A/B?
- 英文答：Online evidence: Deployed, no online results. A/B duration: not reported. A/B traffic: not reported.
- 中文问：Deep Neural Networks for YouTube Recommendations 有线上证据吗，A/B 做了多久？
- 中文答：线上证据：已部署，无线上结果。A/B 时长：未报告。A/B 流量：未报告。
- 引用字段：deployment.online_evidence, deployment.ab_duration, deployment.ab_traffic
- 抽查结论：[ ] 通过  [ ] 有问题

## 14. alibaba-mgoe-2025 / training

- 英文问：How is MGOE trained?
- 英文答：Training mode: Offline. Objectives: Weighted sum of per-task binary cross-entropy with L1 and L2 regularization.
- 中文问：MGOE 是怎么训练的？
- 中文答：训练方式：离线。 训练目标：按任务二元交叉熵加权求和，加 L1 与 L2 正则。
- 引用字段：training.mode, training.objectives
- 抽查结论：[ ] 通过  [ ] 有问题

## 15. alibaba-urm-2025 / what

- 英文问：What is URM, in one sentence?
- 英文答：URM turns a fine-tuned Qwen-7B LLM into a universal generative retriever driven by text objectives; an online A/B lifted advertising revenue +3.01%.
- 中文问：URM 一句话是什么？
- 中文答：URM 把微调后的 Qwen-7B LLM 变成由文本目标驱动的通用生成式检索器；线上 A/B 广告收入 +3.01%。
- 引用字段：tldr
- 抽查结论：[ ] 通过  [ ] 有问题

## 16. twitter-x-for-you-2023 / unknown

- 英文问：What does the source of Twitter For You timeline algorithm not report?
- 英文答：The source does not report: current architecture; A/B results.
- 中文问：Twitter For You timeline algorithm 的原文有哪些没有报告？
- 中文答：原文没有报告：当前的架构；A/B 结果。
- 引用字段：unknown_fields.0, unknown_fields.1
- 抽查结论：[ ] 通过  [ ] 有问题

## 17. kuaishou-oneloc-2025 / inputs

- 英文问：What inputs does OneLoc use?
- 英文答：IDs and tokenization: Geo-aware semantic IDs from residual quantization with 3 codebooks of 8192 clusters. Input signals: Watch, click and pay behavior sequences with location IDs and location context embeddings; User real-time location as a gate and as the decoder query, with surrounding locations as keys and values; Geographic reward by user-store distance and GMV reward for DPO preference pairs.
- 中文问：OneLoc 用了哪些输入？
- 中文答：ID 与 token 化：残差量化 3 个 8192 聚类码本的地理感知语义 ID。 输入特征：带位置 ID 与位置上下文嵌入的观看、点击、支付行为序列；用户实时位置作为门控与解码器 Query，周边位置作为 Key 和 Value；按用户门店距离的地理奖励与 GMV 奖励，用于 DPO 偏好对。
- 引用字段：id_tokenization.approach, features_signals.0, features_signals.1, features_signals.2
- 抽查结论：[ ] 通过  [ ] 有问题

## 18. kuaishou-rqreg-2026 / caveats

- 英文问：What should I keep in mind when reading the results of RQ-Reg?
- 英文答：The paper reports relative lifts over the production baseline; absolute AUC and ADVV values are not published. The A/B allocates 10% of traffic to each arm, matching arms at about 40 million users; bucket construction beyond that is not described.
- 中文问：读 RQ-Reg 的结果时要注意什么？
- 中文答：论文报告相对生产基线的提升；绝对 AUC 与 ADVV 值未公布。 A/B 每臂 10% 流量，两臂各约 4000 万用户；此之外的桶构造未描述。
- 引用字段：caveats.0, caveats.1
- 抽查结论：[ ] 通过  [ ] 有问题

## 19. netflix-recsys-2015 / inputs

- 英文问：What inputs does Netflix Recommender System use?
- 英文答：IDs and tokenization: Video IDs. Input signals: Viewing history; Ratings and other member interactions (as discussed generally); Time of day / device (contextual); Video popularity.
- 中文问：Netflix Recommender System 用了哪些输入？
- 中文答：ID 与 token 化：Video IDs。 输入特征：观看历史；评分和其他成员交互，按一般性的讨论；一天中的时间和设备，上下文特征；视频热度。
- 引用字段：id_tokenization.approach, features_signals.0, features_signals.1, features_signals.2, features_signals.3
- 抽查结论：[ ] 通过  [ ] 有问题

## 20. tiger-google-2023 / online

- 英文问：Does TIGER have online evidence, and how long was the A/B?
- 英文答：Online evidence: No online claim. A/B duration: not reported. A/B traffic: not reported.
- 中文问：TIGER 有线上证据吗，A/B 做了多久？
- 中文答：线上证据：未声称线上效果。A/B 时长：未报告。A/B 流量：未报告。
- 引用字段：deployment.online_evidence, deployment.ab_duration, deployment.ab_traffic
- 抽查结论：[ ] 通过  [ ] 有问题

## 21. kuaishou-quasid-2026 / serving

- 英文问：What serving latency, QPS, cost or hardware does QuaSID report?
- 英文答：Serving latency: not reported. Serving QPS: not reported. Inference cost: not reported. Hardware: not reported.
- 中文问：QuaSID 报告了怎样的服务延迟、QPS、成本和硬件？
- 中文答：服务延迟：未报告。 服务 QPS：未报告。 推理成本：未报告。 硬件：未报告。
- 引用字段：deployment.serving_latency, deployment.serving_qps, deployment.inference_cost, deployment.hardware
- 抽查结论：[ ] 通过  [ ] 有问题

## 22. mmoe-google-2018 / what

- 英文问：What is MMoE, in one sentence?
- 英文答：Multi-gate Mixture-of-Experts gives each task its own gate over shared experts, learning task relationships from data; tested at Google, shared-bottom was the one in production.
- 中文问：MMoE 一句话是什么？
- 中文答：Multi-gate Mixture-of-Experts 让每个任务在共享的 expert 上有自己的 gate，从数据中学习任务之间的关系；在 Google 测试，线上跑的是 shared-bottom。
- 引用字段：tldr
- 抽查结论：[ ] 通过  [ ] 有问题

## 23. linkedin-lirank-2024 / online

- 英文问：Does LiRank have online evidence, and how long was the A/B?
- 英文答：Online evidence: Online numbers. A/B duration: not reported. A/B traffic: not reported.
- 中文问：LiRank 有线上证据吗，A/B 做了多久？
- 中文答：线上证据：有线上数据。A/B 时长：未报告。A/B 流量：未报告。
- 引用字段：deployment.online_evidence, deployment.ab_duration, deployment.ab_traffic
- 抽查结论：[ ] 通过  [ ] 有问题

## 24. alibaba-mmq-2025 / who

- 英文问：Who built MMQ and where does it run?
- 英文答：MMQ comes from Alibaba, 2025. Deployed in: Generative retrieval of a Southeast Asian e-commerce advertising platform.
- 中文问：MMQ 是谁做的，用在哪里？
- 中文答：MMQ 来自 阿里巴巴，2025 年。上线位置：东南亚电商广告平台的生成式检索。
- 引用字段：company, year, deployed_in
- 抽查结论：[ ] 通过  [ ] 有问题

## 25. meta-andromeda-2024 / core

- 英文问：What is the core idea of Meta Andromeda?
- 英文答：A deep neural network co-designed with Grace Hopper hardware and a hierarchical index, trained jointly with retrieval.
- 中文问：Meta Andromeda 的核心思路是什么？
- 中文答：与 Grace Hopper 硬件协同设计的深度神经网络，加与召回联合训练的层级索引。
- 引用字段：core_idea
- 抽查结论：[ ] 通过  [ ] 有问题

## 26. dssm-microsoft-2013 / core

- 英文问：What is the core idea of DSSM?
- 英文答：Project query and document into one semantic space with DNNs over letter-trigram word hashing, and train on clickthrough data to rank clicked documents highest.
- 中文问：DSSM 的核心思路是什么？
- 中文答：用基于字母 trigram 词哈希的 DNN 把查询和文档投影到同一个语义空间，并在点击数据上训练，让被点击的文档排在最前。
- 引用字段：core_idea
- 抽查结论：[ ] 通过  [ ] 有问题

## 27. alibaba-nezha-2025 / caveats

- 英文问：What should I keep in mind when reading the results of NEZHA?
- 英文答：The paper states that the 7-day online test was a reverse A/B test on 10% of traffic; no further bucket detail is given, and the production training setup is not described beyond the semantic-ID configuration shared with the public experiments. Serving latencies in Table 1 are normalized by the 0.6B prefill time for confidentiality, so absolute milliseconds are not published.
- 中文问：读 NEZHA 的结果时要注意什么？
- 中文答：论文说明 7 天线上测试是占 10% 流量的反向 A/B；没有更多分桶细节，生产训练设置除与公开实验共享的语义 ID 配置外未作描述。 表 1 服务延迟按 0.6B 预填充时间归一化以保密，绝对毫秒数未公开。
- 引用字段：caveats.0, caveats.1
- 抽查结论：[ ] 通过  [ ] 有问题

## 28. meta-lattice-2025 / training

- 英文问：How is Meta Lattice trained?
- 英文答：Training mode: Offline with distillation.
- 中文问：Meta Lattice 是怎么训练的？
- 中文答：训练方式：离线，带蒸馏。
- 引用字段：training.mode
- 抽查结论：[ ] 通过  [ ] 有问题

## 29. alibaba-bar-2025 / online

- 英文问：Does BAR have online evidence, and how long was the A/B?
- 英文答：Online evidence: Online numbers. A/B duration: One month. A/B traffic: 10% of online traffic randomly partitioned into two groups; corroborated over the same month by a 50% scaled comparison and a 5% reverse holdout.
- 中文问：BAR 有线上证据吗，A/B 做了多久？
- 中文答：线上证据：有线上数据。A/B 时长：一个月。A/B 流量：10% 线上流量随机分成两组；同周期以 50% 放量对比与 5% 反向留出实验相互印证。
- 引用字段：deployment.online_evidence, deployment.ab_duration, deployment.ab_traffic
- 抽查结论：[ ] 通过  [ ] 有问题

## 30. dssm-microsoft-2013 / caveats

- 英文问：What should I keep in mind when reading the results of DSSM?
- 英文答：Offline evaluation only: the paper reports no A/B test and makes no production deployment claim, and the authors name a commercial search engine without saying whether DSSM served traffic; it is admitted through the exemption for papers cited 500 or more times. Documents are represented by their titles only, and the evaluation set is assumed to contain only new or tail URLs without click information, so the setting is narrower than full web ranking.
- 中文问：读 DSSM 的结果时要注意什么？
- 中文答：只有离线评估：论文没有 A/B 测试，也没有生产部署声明，作者只写了某个商业搜索引擎，没有说 DSSM 是否承接过流量；它是靠被引 500 次以上的例外准入的。 文档只用标题表示，而且评估集假设只含没有点击信息的新 URL 或长尾 URL，所以设定比完整的网页排序窄。
- 引用字段：caveats.0, caveats.1
- 抽查结论：[ ] 通过  [ ] 有问题
