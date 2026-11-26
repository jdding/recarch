# RecArch 全库复审 · 2026-11-26

覆盖线上基线 `3af089f` 的 **126 张活跃系统卡和 6 个专题**。这轮按中英文摘要、关键结果、对照与流量、生产上线状态、效率测量条件和公开出处逐卡检查。优先用原论文的实验表、补充材料和作者或团队公开的一手技术资料。版本不同的结果按各自口径处理。

**22 张卡有本轮新增改动**，其中 19 张修正事实、适用范围或容易误读的实验口径，3 张补入更早可公开访问的作者版本。另有 8 张为上一轮已经完成的本地更新。本轮同步修正 2 个专题，并更新受影响的 FAQ 和评测答案。

本轮有 123 张可查看原文或团队公开技术资料。另有 3 张的细节待重读出版全文。DPGR 和 NextGen 的主要指标已与官方会议作者摘要核对，Unity 的线上精确读数仍依赖仓库已有定稿摘录。区分这三处材料限制和来源本身未披露的字段。

Zotero KB 的只读连接可用，要求确认当前版本的查询未取得实时版本探测结果。复审使用公开来源，历史快照没有作为本轮证据。

## 专题复核

| 专题 | 处理 |
|---|---|
| [生成式召回](../data/topics/generative-retrieval.yaml) | 更正 DPGR 的实验结构，区别直接替换召回器、添加通道与在生产流量上试验。 |
| [Semantic ID 与物品分词](../data/topics/semantic-id-tokenization.yaml) | 更正 NEZHA 的合法 ID 密度与草稿合法率，以及 FLUID 的冷启动直播间观看指标。 |
| [长用户序列建模](../data/topics/long-user-sequence-modeling.yaml) | 核对请求时、批量与缓存方案。PinFM、PinnerFormer 等结果从修正后的系统卡读取。 |
| [推荐算法的 RSI](../data/topics/recommendation-rsi.yaml) | 核对线上晋级模型的结果、代理验证过程与离线评测各自的出处。 |
| [Agent 如何使用推荐能力](../data/topics/agentic-recommendation.yaml) | 核对工具调用、近线召回、在线反馈重排的运行位置，按完整体验或特定组件的实验边界描述。 |
| [端云协同推荐](../data/topics/device-cloud-recommendation.yaml) | 核对端侧重排、缓存替换、端侧发起查询与云召回的分工，以及覆盖份额和时延的不同口径。 |

## 系统卡复审记录

「保留」表示本轮检查的重点字段未发现需要修改的证据冲突。表中记录本轮实际使用的证据，卡片继续列出完整书目。

| 卡片 | 结论 | 核对内容及出处 |
|---|---|---|
| [airbnb-listing-embeddings-2018](../data/systems/airbnb-listing-embeddings-2018.yaml) | 保留 | 第 4.3、4.4 节分别做轮播和搜索排序实验，两者结果均有各自入口。 [原文或官方资料](https://raw.githubusercontent.com/wzhe06/Ad-papers/master/Embedding/%5BAirbnb%20Embedding%5D%20Real-time%20Personalization%20using%20Embeddings%20for%20Search%20Ranking%20at%20Airbnb%20%28Airbnb%202018%29.pdf) · [Airbnb 工程文章](https://medium.com/airbnb-engineering/listing-embeddings-for-similar-listing-recommendations-and-real-time-personalization-in-search-601172f7603e) |
| [airbnb-maps-ranking-2024](../data/systems/airbnb-maps-ranking-2024.yaml) | 修订 | 区分移动端图钉随机化与独立的精简图钉实验。摘要采用大规模实验的未取消预订 +1.9%。 [原文或官方资料](https://arxiv.org/pdf/2407.00091) |
| [airbnb-search-dnn-2018](../data/systems/airbnb-search-dnn-2018.yaml) | 保留 | 作者报告分阶段上线与预订改善。卡片保留定性线上结论。 [原文或官方资料](https://arxiv.org/abs/1810.09591) |
| [alibaba-bar-2025](../data/systems/alibaba-bar-2025.yaml) | 保留 | 线上收入与 RPM 看业务 A/B，RIR 和 IIR 看全召回链路的覆盖变化。 [原文或官方资料](https://arxiv.org/pdf/2508.05206) |
| [alibaba-degre-2026](../data/systems/alibaba-degre-2026.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 GMV、Orders。 [原文或官方资料](https://arxiv.org/pdf/2605.25749) |
| [alibaba-edgerec-2020](../data/systems/alibaba-edgerec-2020.yaml) | 保留 | 两轮生产实验区分云端候选与设备排序，系统响应与端上动作捕获各自报告。 [原文或官方资料](https://arxiv.org/pdf/2005.08416) |
| [alibaba-forge-2025](../data/systems/alibaba-forge-2025.yaml) | 保留 | 第 4.3.6 节与表 5 确认相比基础 SID 配方的结果。成交笔数指标口径未定义。 [原文或官方资料](https://arxiv.org/pdf/2509.20904) |
| [alibaba-hisac-2026](../data/systems/alibaba-hisac-2026.yaml) | 修订 | 第 4.7 节表 3 的业务 A/B 与缓存命中条件下的延迟、投影 FLOPs 分开。 [原文或官方资料](https://arxiv.org/pdf/2602.21009v2) |
| [alibaba-lum-2025](../data/systems/alibaba-lum-2025.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 CTR、RPM。 [原文或官方资料](https://arxiv.org/pdf/2502.08309) |
| [alibaba-mgoe-2025](../data/systems/alibaba-mgoe-2025.yaml) | 保留 | 表中同时给 MMoE 与 MacGNN 对照。推理速度来自离线基准。 [原文或官方资料](https://arxiv.org/pdf/2506.10520) |
| [alibaba-mine-then-train-2026](../data/systems/alibaba-mine-then-train-2026.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 CTR、RPM。 [原文或官方资料](https://arxiv.org/pdf/2608.24091) |
| [alibaba-mmq-2025](../data/systems/alibaba-mmq-2025.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 Advertising Revenue、Conversion Rate。 [原文或官方资料](https://arxiv.org/pdf/2508.15281) |
| [alibaba-muse-2025](../data/systems/alibaba-muse-2025.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 CTR、RPM。 [原文或官方资料](https://arxiv.org/pdf/2512.07216) |
| [alibaba-nezha-2025](../data/systems/alibaba-nezha-2025.yaml) | 修订 | 第 3.3 节的 0.1% 是合法 ID 占整个编码空间的比例。43% 到 93% 以上才是生产数据上的合法草稿占比。 [原文或官方资料](https://arxiv.org/pdf/2511.18793) |
| [alibaba-recbot-2025](../data/systems/alibaba-recbot-2025.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 Negative feedback frequency、GMV。 [原文或官方资料](https://arxiv.org/html/2509.21317) |
| [alibaba-resid-2026](../data/systems/alibaba-resid-2026.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 Ad revenue、CTR。 [原文或官方资料](https://arxiv.org/html/2611.16404v1) |
| [alibaba-sort-2026](../data/systems/alibaba-sort-2026.yaml) | 修订 | 四场景对线上 DLRM 的结果与同模型服务优化基准分开，FLOPs 单列。 [原文或官方资料](https://arxiv.org/pdf/2603.03988) |
| [alibaba-urm-2025](../data/systems/alibaba-urm-2025.yaml) | 前批改动复核 | 表 6 的广告 A/B 与附录 B.4 的模型 p99 基准分开。 [原文或官方资料](https://arxiv.org/pdf/2502.03041v2) |
| [amap-gplan-2026](../data/systems/amap-gplan-2026.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 UV-CTR。 [原文或官方资料](https://arxiv.org/pdf/2605.28888) |
| [amap-gwhere-2026](../data/systems/amap-gwhere-2026.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 P-CTR、U-CTR。 [原文或官方资料](https://arxiv.org/pdf/2607.26073v1) |
| [amap-intsr-2025](../data/systems/amap-intsr-2025.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 GMV、CTR。 [原文或官方资料](https://arxiv.org/pdf/2509.21179) |
| [amazon-cosmo-2024](../data/systems/amazon-cosmo-2024.yaml) | 保留 | 第 4.3.2 节。测的是约 10% 美国流量中接入 COSMO 的搜索导航。 [原文或官方资料](https://assets.amazon.science/19/5d/bde30d0d4019be6421e79e50cda9/cosmo-paper.pdf) |
| [amazon-item-to-item-2003](../data/systems/amazon-item-to-item-2003.yaml) | 修订 | 开篇的半秒是实时应用要求。去掉比较表中的实测延迟写法。 [原文或官方资料](https://www.cs.umd.edu/~samir/498/Amazon-Recommendations.pdf) |
| [baidu-icegr-2026](../data/systems/baidu-icegr-2026.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 Order volume、CTR。 [原文或官方资料](https://arxiv.org/html/2608.29652v3) |
| [baidu-unique-2026](../data/systems/baidu-unique-2026.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 Total watch duration、Total distribution volume。 [原文或官方资料](https://arxiv.org/pdf/2609.23718) |
| [bytedance-fluid-2026](../data/systems/bytedance-fluid-2026.yaml) | 补公开来源 | 找到五月公开作者稿，核实第 4.2 节表 4。正式书目保留。 [原文或官方资料](https://arxiv.org/html/2605.21832v2#S4.SS2) |
| [bytedance-gear-2026](../data/systems/bytedance-gear-2026.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 ADSS、ADVV。 [原文或官方资料](https://arxiv.org/pdf/2609.39327) |
| [bytedance-hap-2026](../data/systems/bytedance-hap-2026.yaml) | 前批改动复核 | 正式线上对照与第 4.5.1 节路由消融分开。 [原文或官方资料](https://arxiv.org/html/2603.03770v1) |
| [bytedance-lemur-2025](../data/systems/bytedance-lemur-2025.yaml) | 修订 | 第 4.3 节与摘要对抖音 0.843% 的表述不一致。抖音保留显著下降，第 4.7 节另列 TikTok 的定量结果。 [原文或官方资料](https://arxiv.org/html/2511.10962v2) |
| [bytedance-longer-2025](../data/systems/bytedance-longer-2025.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 ADSS / ADVV。 [原文或官方资料](https://arxiv.org/pdf/2505.04421) |
| [bytedance-mixformer-2026](../data/systems/bytedance-mixformer-2026.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 Active Day、Duration。 [原文或官方资料](https://arxiv.org/pdf/2602.14110) |
| [bytedance-onetrans](../data/systems/bytedance-onetrans.yaml) | 保留 | 以 GSR 版本第 6.7 节为准。复购观察窗 14 天，主 A/B 一周。 [原文或官方资料](https://arxiv.org/html/2611.04720v1#S6.SS7) |
| [bytedance-rankmixer-2025](../data/systems/bytedance-rankmixer-2025.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 Active days、Total in-app duration。 [原文或官方资料](https://arxiv.org/pdf/2507.15551) |
| [bytedance-sequenceo1-2026](../data/systems/bytedance-sequenceo1-2026.yaml) | 修订 | 附录 G.6 的 100K FLOPs 为分支在假设复用率和命中率下的估算，分开写训练与推理。 [原文或官方资料](https://arxiv.org/pdf/2609.08443) |
| [dcn-google](../data/systems/dcn-google.yaml) | 保留 | 核对生产实验或作者描述的定性结果，包括 Online business metrics。 [原文或官方资料](https://arxiv.org/pdf/2008.13535) |
| [deepfm-huawei-2017](../data/systems/deepfm-huawei-2017.yaml) | 保留 | 核对离线范围。 [原文或官方资料](https://arxiv.org/abs/1703.04247) |
| [dien-taobao-2018](../data/systems/dien-taobao-2018.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 CTR、PPC。 [原文或官方资料](https://arxiv.org/pdf/1809.03672) |
| [din-alibaba-2017](../data/systems/din-alibaba-2017.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 CTR、RPM。 [原文或官方资料](https://arxiv.org/pdf/1706.06978) |
| [dlrm-meta-2019](../data/systems/dlrm-meta-2019.yaml) | 保留 | 核对离线范围。 [原文或官方资料](https://arxiv.org/abs/1906.00091) |
| [doordash-homepage-2022](../data/systems/doordash-homepage-2022.yaml) | 保留 | 官方文章报告既有用户的定性收益。混合实体首页仍在开发。 [原文或官方资料](https://careersatdoordash.com/blog/homepage-recommendation-with-exploitation-and-exploration/) |
| [dssm-microsoft-2013](../data/systems/dssm-microsoft-2013.yaml) | 保留 | 核对离线范围。 [原文或官方资料](https://posenhuang.github.io/papers/cikm2013_DSSM_fullversion.pdf) |
| [eleme-dte-2026](../data/systems/eleme-dte-2026.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 CTR、RPM。 [原文或官方资料](https://arxiv.org/pdf/2608.16274) |
| [esmm-alibaba-2018](../data/systems/esmm-alibaba-2018.yaml) | 修订 | 把无样本选择偏差的保证改成以全曝光空间训练来缓解偏差。论文唯有离线证据。 [原文或官方资料](https://arxiv.org/pdf/1804.07931) |
| [facebook-search-ebr-2020](../data/systems/facebook-search-ebr-2020.yaml) | 保留 | 核对生产实验或作者描述的定性结果，包括 Online metrics。 [原文或官方资料](https://arxiv.org/pdf/2006.11632) |
| [glmix-linkedin-2016](../data/systems/glmix-linkedin-2016.yaml) | 修订 | 第 2.1 节把指标定义为申请按钮点击，图 6 对照 LR-Cosine。第 4.2 节说明离线打分与在线读取部署。 [原文或官方资料](https://kdd.org/kdd2016/papers/files/adf0562-zhangA.pdf) |
| [google-ads-ftrl-2013](../data/systems/google-ads-ftrl-2013.yaml) | 保留 | 核对生产实验或作者描述的定性结果。 [原文或官方资料](https://research.google.com/pubs/archive/41159.pdf) |
| [google-discover-sdf-2026](../data/systems/google-discover-sdf-2026.yaml) | 前批改动复核 | 表 3 的两个月保留组结果与公式 8 的误差估计分开核对。 [原文或官方资料](https://arxiv.org/html/2608.15780v1) |
| [google-recevolve-2026](../data/systems/google-recevolve-2026.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 User satisfaction、Unique content。 [原文或官方资料](https://arxiv.org/html/2609.01622v1) |
| [hstu-meta-2024](../data/systems/hstu-meta-2024.yaml) | 保留 | 保留作者给出的 topline 汇总。产品指标和完整对照配置未披露。 [原文或官方资料](https://arxiv.org/pdf/2402.17152) |
| [huawei-hpgr-2026](../data/systems/huawei-hpgr-2026.yaml) | 补公开来源 | 找到三月带 WWW DOI 的作者版，第 5 节表 3 核实 7 天、等分流量和 eCPM +1.99%。 [原文或官方资料](https://arxiv.org/html/2603.00980v1#S5) |
| [instagram-explore-2023](../data/systems/instagram-explore-2023.yaml) | 保留 | 核对公开的部署说明。 [原文或官方资料](https://engineering.fb.com/2023/08/09/ml-applications/scaling-instagram-explore-recommendations-system/) |
| [jd-gcrank-2026](../data/systems/jd-gcrank-2026.yaml) | 补公开来源 | 找到一月公开作者版本，第 5.5 节核实三项线上指标和 TP99。保持正式版出处。 [原文或官方资料](https://arxiv.org/html/2601.02361v1#S5.SS5) |
| [kuaishou-agentx](../data/systems/kuaishou-agentx.yaml) | 保留 | 九月版上线评审表区分不同场景、客户端以及独立的研究过程指标。 [原文或官方资料](https://arxiv.org/html/2609.30001v1) |
| [kuaishou-capts-2026](../data/systems/kuaishou-capts-2026.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 Total app time spent、Average app time spent per device。 [原文或官方资料](https://arxiv.org/pdf/2602.12564) |
| [kuaishou-evorec-2026](../data/systems/kuaishou-evorec-2026.yaml) | 保留 | 表 6 分全量受试用户与高意向子群，线上收益来自新增近线召回通道。 [原文或官方资料](https://arxiv.org/html/2611.01977v1) |
| [kuaishou-glorank-2026](../data/systems/kuaishou-glorank-2026.yaml) | 保留 | 表 4 的线上对照 GoalRank，试验组与对照组流量相同。 [原文或官方资料](https://arxiv.org/pdf/2604.25291v1) |
| [kuaishou-nar4rec-2024](../data/systems/kuaishou-nar4rec-2024.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 Views、Complete views。 [原文或官方资料](https://arxiv.org/html/2402.06871v6) |
| [kuaishou-on-device-video-2022](../data/systems/kuaishou-on-device-video-2022.yaml) | 保留 | 端上两平台的模型与搜索耗时，以及上下文重排对照，均分开核对。 [原文或官方资料](https://arxiv.org/pdf/2208.09577v2) |
| [kuaishou-oneloc-2025](../data/systems/kuaishou-oneloc-2025.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 GMV、Order volume。 [原文或官方资料](https://arxiv.org/pdf/2508.14646) |
| [kuaishou-onemall-2026](../data/systems/kuaishou-onemall-2026.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 GMV。 [原文或官方资料](https://arxiv.org/pdf/2601.21770) |
| [kuaishou-onesearch-2025](../data/systems/kuaishou-onesearch-2025.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 Search PVs、Item CTR。 [原文或官方资料](https://arxiv.org/pdf/2509.03236) |
| [kuaishou-playback-grf-2024](../data/systems/kuaishou-playback-grf-2024.yaml) | 保留 | 总体观看时长、弱网用户观看时长和两个组件耗时各有范围。 [原文或官方资料](https://arxiv.org/pdf/2410.05863) |
| [kuaishou-quasid-2026](../data/systems/kuaishou-quasid-2026.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 GMV-S2、GMV-S1。 [原文或官方资料](https://arxiv.org/pdf/2603.00632v1) |
| [kuaishou-recharness-2026](../data/systems/kuaishou-recharness-2026.yaml) | 保留 | 第 3.5 节表 4。在线评的是入选排序改动，代理本身的对比另在离线。 [原文或官方资料](https://arxiv.org/html/2607.29241v2) |
| [kuaishou-rqreg-2026](../data/systems/kuaishou-rqreg-2026.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 ADVV。 [原文或官方资料](https://arxiv.org/pdf/2602.23012) |
| [kuaishou-sarm-2026](../data/systems/kuaishou-sarm-2026.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 Watch Time、Gift。 [原文或官方资料](https://arxiv.org/pdf/2602.09401) |
| [linkedin-feed-sr-2026](../data/systems/linkedin-feed-sr-2026.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 Time spent、Likes, comments and shares。 [原文或官方资料](https://arxiv.org/pdf/2602.12354) |
| [linkedin-lignn-2024](../data/systems/linkedin-lignn-2024.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 Online CTR、Feed engaged DAU。 [原文或官方资料](https://arxiv.org/pdf/2402.11139) |
| [linkedin-lirank-2024](../data/systems/linkedin-lirank-2024.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 CTR、Qualified job applications。 [原文或官方资料](https://arxiv.org/pdf/2402.06859) |
| [linkedin-semantic-search-2026](../data/systems/linkedin-semantic-search-2026.yaml) | 保留 | 表 11、13 的 GPU 吞吐和流量调度来自固定延迟预算的基准。48% 对应高峰每查询 GPU 计算。 [原文或官方资料](https://arxiv.org/pdf/2602.07309v1) |
| [meituan-dpgr-2026](../data/systems/meituan-dpgr-2026.yaml) | 修订 | 会议作者摘要确认四个线上指标。依据原卡表 5 记录，三意图的峰时延迟高于单意图。分流、对照和表 5 本轮待重读全文。 [可访问的一手资料](https://recsys.acm.org/recsys26/session-2/) |
| [meituan-mtgenrec-2025](../data/systems/meituan-mtgenrec-2025.yaml) | 修订 | 2% 分流只与表 1 的 4G、110G 变体读数绑定。与 MTGR 摘要重合的两个数字无法确认为独立 A/B。 [原文或官方资料](https://arxiv.org/pdf/2505.12663) |
| [meituan-mtgr-2025](../data/systems/meituan-mtgr-2025.yaml) | 保留 | 正文报告生产 DLRM 对照及推理成本。与 MTGenRec 的重复摘要读数不能当成独立样本。 [原文或官方资料](https://arxiv.org/pdf/2505.18654) |
| [meituan-sif-2026](../data/systems/meituan-sif-2026.yaml) | 前批改动复核 | 第 4.1 节的训练硬件和第 4.5 节的七天线上读数分开。 [原文或官方资料](https://arxiv.org/html/2604.15650v3) |
| [meta-andromeda-2024](../data/systems/meta-andromeda-2024.yaml) | 修订 | 官方文章把选定流量细分限定到 +8% 广告质量。+6% 召回和广告质量均未披露实验配置。 [原文或官方资料](https://engineering.fb.com/2024/12/02/production-engineering/meta-andromeda-advantage-automation-next-gen-personalized-ads-retrieval-engine/) |
| [meta-gem-2025](../data/systems/meta-gem-2025.yaml) | 保留 | 各季度转化读数见初版工程文章。2026 年新版的跨曲面数字采用独立的工程文章。 [原文或官方资料](https://engineering.fb.com/2025/11/10/ml-applications/metas-generative-ads-model-gem-the-central-brain-accelerating-ads-recommendation-ai-innovation/) · [2026 代官方结果](https://engineering.fb.com/2026/10/13/ml-applications/generative-ads-model-gem-scaling-frontier-ads-ai/) |
| [meta-kunlun-2026](../data/systems/meta-kunlun-2026.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 Topline metrics。 [原文或官方资料](https://arxiv.org/pdf/2602.10016) |
| [meta-lattice-2025](../data/systems/meta-lattice-2025.yaml) | 前批改动复核 | 第 4.5 节的汇总收益和电力容量，按原文保留范围。 [原文或官方资料](https://arxiv.org/pdf/2512.09200v2) |
| [meta-llatte-2026](../data/systems/meta-llatte-2026.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 Conversion、NE。 [原文或官方资料](https://arxiv.org/pdf/2601.20083) |
| [meta-mpzch-2026](../data/systems/meta-mpzch-2026.yaml) | 修订 | 表 3 的 NE 改善为分享 0.38%、观看时长 0.12%、100% 播放 0.12%、跳过 0.09%。训练 QPS 移出服务吞吐。 [原文或官方资料](https://arxiv.org/pdf/2602.17050) |
| [meta-rankgraph2-2026](../data/systems/meta-rankgraph2-2026.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 CTR、CVR。 [原文或官方资料](https://arxiv.org/pdf/2606.18379) |
| [meta-shape-your-feed-2026](../data/systems/meta-shape-your-feed-2026.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 Post dislike、Post dismiss。 [原文或官方资料](https://arxiv.org/pdf/2608.06632) |
| [meta-unity-2026](../data/systems/meta-unity-2026.yaml) | 部分待复核 | KDD 和官方代码确认系统与公开实验。Pollen 的两个精确 WatchTime 读数沿用既有定稿摘录，本轮全文未重读。 [可访问的一手资料](https://github.com/facebookresearch/unity) · [KDD 正式书目](https://doi.org/10.1145/3770855.3818505) |
| [meta-vlm-2026](../data/systems/meta-vlm-2026.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 Metric-Topline、Metrics-C。 [原文或官方资料](https://arxiv.org/pdf/2604.24806) |
| [mind-tmall-2019](../data/systems/mind-tmall-2019.yaml) | 保留 | 核对生产实验或作者描述的定性结果，包括 CTR。 [原文或官方资料](https://arxiv.org/pdf/1904.08030) |
| [mmoe-google-2018](../data/systems/mmoe-google-2018.yaml) | 保留 | 表 4 核对两层对照。MMoE 的 +2.65% 为对共享底座的满意度增量。 [原文或官方资料](https://openreview.net/pdf?id=ZRSc66YKjNj) |
| [netflix-foundation-model-2025](../data/systems/netflix-foundation-model-2025.yaml) | 保留 | Netflix 的接入文章写明三种方案用于生产，公开文章不报精确线上收益。 [原文或官方资料](https://netflixtechblog.com/integrating-netflixs-foundation-model-into-personalization-applications-cf176b5860eb) |
| [netflix-genpage-2026](../data/systems/netflix-genpage-2026.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 Core engagement metric、End-to-end serving latency。 [原文或官方资料](https://arxiv.org/pdf/2606.31031) |
| [netflix-recsys-2015](../data/systems/netflix-recsys-2015.yaml) | 保留 | 超过 10 亿美元是作者的年度业务价值估计。该节没有对应 A/B 对照。 [原文或官方资料](https://ailab-ua.github.io/courses/resources/netflix_recommender_system_tmis_2015.pdf) |
| [onerec-kuaishou](../data/systems/onerec-kuaishou.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 App Stay Time。 [原文或官方资料](https://arxiv.org/pdf/2508.20900) |
| [pinnerformer-2022](../data/systems/pinnerformer-2022.yaml) | 修订 | 表 7 的 +1% 是全站使用时长，对照是使用聚合 PinnerSage 的首页排序器。 [原文或官方资料](https://arxiv.org/abs/2205.04507) |
| [pinsage-2018](../data/systems/pinsage-2018.yaml) | 保留 | 第 4.4 节对回存率给出 10–30%，卡片沿用该精确指标。 [原文或官方资料](https://arxiv.org/pdf/1806.01973) |
| [pinterest-omnisage-2025](../data/systems/pinterest-omnisage-2025.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 Sitewide repins, also called saves。 [原文或官方资料](https://arxiv.org/pdf/2504.17811) |
| [pinterest-pinfm-2025](../data/systems/pinterest-pinfm-2025.yaml) | 修订 | 表 7 的线上新内容收藏为首页 +5.70%、相关推荐 −0.82%。表 2 是单独的离线冷启动对比。 [原文或官方资料](https://arxiv.org/pdf/2507.12704) |
| [pinterest-pinrec-2025](../data/systems/pinterest-pinrec-2025.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 Search saves、Search fulfillment rate。 [原文或官方资料](https://arxiv.org/abs/2504.10507) |
| [pinterest-transact](../data/systems/pinterest-transact.yaml) | 保留 | 线上 Homefeed A/B、在线推理压测环境和优化前后基准各有范围。 [原文或官方资料](https://arxiv.org/pdf/2506.02267) |
| [pixie-pinterest-2018](../data/systems/pixie-pinterest-2018.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 Engagement per pin。 [原文或官方资料](https://arxiv.org/pdf/1711.07601) |
| [related-pins-pinterest-2017](../data/systems/related-pins-pinterest-2017.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 Propensity to save and click、Local-language share of impressions。 [原文或官方资料](https://arxiv.org/pdf/1702.07969) |
| [shopify-sid-llm-2026](../data/systems/shopify-sid-llm-2026.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 Attributed orders、Converting users。 [原文或官方资料](https://arxiv.org/html/2611.08804v1) |
| [sim-alibaba-2020](../data/systems/sim-alibaba-2020.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 CTR、RPM。 [原文或官方资料](https://arxiv.org/pdf/2006.05639) |
| [snap-snaplgr-2026](../data/systems/snap-snaplgr-2026.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 View Time、Time Spent。 [原文或官方资料](https://arxiv.org/pdf/2607.28895) |
| [spotify-conversational-agent-2026](../data/systems/spotify-conversational-agent-2026.yaml) | 保留 | 第 4.3 节。效果针对扩展 DJ 体验，旧体验仅能调整当前会话。 [原文或官方资料](https://arxiv.org/html/2609.30297v1) |
| [spotify-glide-2026](../data/systems/spotify-glide-2026.yaml) | 前批改动复核 | 第 4.4 和 5.3 节。播客非习惯播放与同延迟目标的吞吐各用独立口径。 [原文或官方资料](https://arxiv.org/html/2603.17540v1) |
| [taobao-aigq-2026](../data/systems/taobao-aigq-2026.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 Attributed GMV、Attributed orders。 [原文或官方资料](https://arxiv.org/pdf/2603.19710) |
| [taobao-cq-sid-2026](../data/systems/taobao-cq-sid-2026.yaml) | 前批改动复核 | 第 4.5 节核对召回服务平均延迟和吞吐的设备范围。 [原文或官方资料](https://arxiv.org/pdf/2605.14434v2) |
| [taobao-nextgen-2026](../data/systems/taobao-nextgen-2026.yaml) | 部分待复核 | 会议作者摘要确认妙杀 GMV +18.85%、订单 +12.35% 和上线。详细对照、CTR、分流和延迟仍依赖既有全文摘录。 [可访问的一手资料](https://recsys.acm.org/recsys26/contributions/) |
| [taobao-recgpt-mobile](../data/systems/taobao-recgpt-mobile.yaml) | 保留 | 第 10.4 节表 8 为曝光与覆盖的绝对份额，图 12 是独立查询服务基准。 [原文或官方资料](https://arxiv.org/abs/2608.24295) |
| [tencent-gpr-2025](../data/systems/tencent-gpr-2025.yaml) | 修订 | v0.4 PTD 的 GMV 幅度按表 4 引 +0.71%，同时标注正文写 +0.58%。 [原文或官方资料](https://arxiv.org/pdf/2511.10138) |
| [tencent-higr-2025](../data/systems/tencent-higr-2025.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 Watch Time、Video Views。 [原文或官方资料](https://arxiv.org/pdf/2512.24787) |
| [tencent-hit-2025](../data/systems/tencent-hit-2025.yaml) | 前批改动复核 | 第 5.5 节表 4 与正文 GMV 幅度的差异在卡片提示。 [原文或官方资料](https://arxiv.org/html/2505.19849v2) |
| [tencent-lfm4ads-2025](../data/systems/tencent-lfm4ads-2025.yaml) | 修订 | v2 第 5.4 节为 CTCVR +3.34%、独立召回 GMV +1.17%。v1 的 5% 流量和 GMV 持平单列。表 3 的双分支 AUC 差值为 0.0005。 [原文或官方资料](https://arxiv.org/html/2508.14948v2) |
| [tencent-nova-2026](../data/systems/tencent-nova-2026.yaml) | 保留 | 第 5.7 节表 4 是入选架构的小流量实验，扩大推广仍是计划。 [原文或官方资料](https://arxiv.org/html/2606.27243v3) |
| [tencent-sgrec-2026](../data/systems/tencent-sgrec-2026.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 GMV、GMV-Normal。 [原文或官方资料](https://arxiv.org/pdf/2602.10606) |
| [tencent-tgr-2026](../data/systems/tencent-tgr-2026.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 CTR、Advertising revenue。 [原文或官方资料](https://arxiv.org/pdf/2609.00986v1) |
| [tencent-tlow-2026](../data/systems/tencent-tlow-2026.yaml) | 修订 | 表 6 的单域通路 UCTR 与整体 CTR 分开。两周是训练时长，线上测试时长未披露。 [原文或官方资料](https://arxiv.org/pdf/2608.24176) |
| [tiger-google-2023](../data/systems/tiger-google-2023.yaml) | 保留 | 公开数据集实验，作为 Semantic ID 方法参照保留。 [原文或官方资料](https://arxiv.org/abs/2305.05065) |
| [twitter-wtf-2013](../data/systems/twitter-wtf-2013.yaml) | 保留 | 核对生产实验或作者描述的定性结果，包括 Connections created。 [原文或官方资料](https://stanford.edu/~rezab/papers/wtf_overview.pdf) |
| [uber-eats-two-tower-2023](../data/systems/uber-eats-two-tower-2023.yaml) | 保留 | 官方文章确认两塔服务架构。相关论文的规模与训练结果不作首页 A/B 归因。 [原文或官方资料](https://www.uber.com/us/en/blog/innovative-recommendation-applications-using-two-tower-embeddings/) |
| [wide-and-deep-google-play-2016](../data/systems/wide-and-deep-google-play-2016.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 App acquisition。 [原文或官方资料](https://arxiv.org/pdf/1606.07792) |
| [x-for-you](../data/systems/x-for-you.yaml) | 保留 | 按卡片固定的官方代码版本核对检索和打分，公开代码未提供线上收益。 [原文或官方资料](https://github.com/xai-org/x-algorithm/blob/52d45989090e63992ba04e4f6cfccd73bf8cc05c/phoenix/README.md) |
| [yandex-argus-2025](../data/systems/yandex-argus-2025.yaml) | 保留 | 核对公开的定量结果和所测场景，包括 Total listening time、Like likelihood。 [原文或官方资料](https://arxiv.org/pdf/2507.15994) |
| [youtube-dnn-2016](../data/systems/youtube-dnn-2016.yaml) | 保留 | 核对生产实验或作者描述的定性结果，包括 Watch time。 [原文或官方资料](https://static.googleusercontent.com/media/research.google.com/zh-CN//pubs/archive/45530.pdf) |
| [youtube-plum-2025](../data/systems/youtube-plum-2025.yaml) | 保留 | 核对生产实验或作者描述的定性结果，包括 Retrieval quality。 [原文或官方资料](https://arxiv.org/abs/2510.07784) |
| [youtube-reinforce-topk-2019](../data/systems/youtube-reinforce-topk-2019.yaml) | 保留 | 第 6.2 节分别给探索流量与 top-K 校正的 ViewTime，两个数字来自不同实验。 [原文或官方资料](https://arxiv.org/pdf/1812.02353) |
| [youtube-self-evolving-recsys-2026](../data/systems/youtube-self-evolving-recsys-2026.yaml) | 保留 | 按改动读两级指标与区间。线上结果来自晋级后的模型。 [原文或官方资料](https://arxiv.org/html/2602.10226) |
| [youtube-sidec-2026](../data/systems/youtube-sidec-2026.yaml) | 修订 | 第 3.1、3.4 节的存储和训练 I/O 与服务推理开销分开。表 1 线上指标保留。 [原文或官方资料](https://arxiv.org/pdf/2607.24865) |
