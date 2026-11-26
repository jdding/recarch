# RecArch 开发与维护说明

本文档面向维护者，说明数据模型、构建校验、双语规则、测试、日常维护和部署。卡片字段的完整定义以 [`schema/schema.md`](../schema/schema.md) 为准，收录与排期规则以 [`admission.md`](admission.md) 为准。

## 1. 架构

RecArch 是纯静态站点。`build.py` 读取 `data/` 下的 YAML，校验后生成 `dist/`，包括中英文两套页面、`sitemap.xml`、`feed.xml` 和 `robots.txt`。本地使用与 Pages CI 一致的 Python 3.12。

```bash
pip install -r requirements.txt
SITE_URL=https://jdding.github.io/recarch python3 build.py
cd dist && python3 -m http.server 8080
```

`SITE_URL` 决定 canonical 链接和 sitemap 中的域名，本地预览可以不设。

## 2. 数据模型

### 2.1 卡片与状态

- 每个系统一个文件：`data/systems/<id>.yaml`。
- `status` 取 `active`、`superseded` 或 `retired`。只有 `active` 卡片会发布；其余两类不生成页面、不进归档、不产生动态，也不留重定向，文件保留在仓库中供准入审计使用。
- 一个系统只有一张卡。多版本系统用 `version` / `versions` 字段合并，展示最新版本，旧版本只在版本历史中列出名称和论文链接。合并后的引用数按各版本求和，任一版本有官方代码即视为有代码。
- 作者撤稿的论文移到 `data/withdrawn/`。

### 2.2 发布前提：全文

- 卡片必须基于来源全文，有正式发表版本时以正式版为 `primary_source`。
- 只读过摘要或检索片段的条目放在 `data/drafts/`，带 `needs_fulltext: true` 和 `fulltext_note`，不参与构建。
- 所有数字都必须能在全文中找到；没有报告的字段写「未报告」，不估算。
- 仓库中不存放任何论文 PDF 或原文文件，`.gitignore` 已排除 `*.pdf` 和 `zotero/`。

### 2.3 年份与范式

- `year` 是首次公开披露的年份。
- `era` 是主导范式，取 `classic`、`deep` 或 `generative`，显式填写并由构建校验，不按年份推断。
- 首页的范式和阶段筛选由 `data/taxonomy.yaml` 映射。每个范式标签恰好属于一个大类，每个流水线阶段恰好属于一个阶段组；未映射、重复映射或未知的标签都会让构建失败。

### 2.4 部署信息

部署字段统一为：上线场景、流量和 A/B 时长、对照基线、线上指标涨幅、训练算力、推理延迟和成本。`online_evidence` 标明线上证据的强弱，从有具体数字的 A/B 结果到没有线上声明，共四档。

### 2.5 代码

每张卡都有 `code` 字段，状态分为官方完整代码、官方部分代码、仅第三方实现和未找到。「未找到」只记录检索结果，不代表确实没有代码。

### 2.6 引用数

`scripts/citations.py` 生成 `data/citations.json`，该文件提交到仓库。

- 查找顺序：先用 DOI 查 Semantic Scholar，再用 arXiv id，最后用标题检索（标题相似度至少 0.92，年份相差不超过 1 才采纳）；OpenAlex 作为兜底。
- 不抓取 Google Scholar。
- 同一论文在 Semantic Scholar 被拆成会议版和 arXiv 版时，两者计数相加，并在条目中注明。
- 只有博客或代码、没有论文的卡片不显示引用数，页面上不会出现「0」。
- 查询失败时保留上一次的值。

### 2.7 架构图

`data/diagrams/<id>.yaml` 是我们自己重绘的简化架构图，由 `build.py` 渲染成内联 SVG。图注中的链接必须是该卡片 `sources` 中的某个 URL，否则构建失败。

### 2.8 专题页

`data/topics/<slug>.yaml` 定义专题对比页。页面上的统计、年份、范式分布和公司标识全部从卡片数据计算，专题页不会出现卡片里没有的数字。公司标识只用字母，不使用第三方 logo。

## 3. 双语

- 中文是默认语言，位于站点根目录；英文位于 `/en/`，每个页面都有语言切换。
- 翻译放在 `data/i18n/`：新卡片需要 `data/i18n/zh/systems/<id>.txt`，新专题需要 `data/i18n/zh/topics/<slug>.yaml`，新一期周报需要 `*_zh` 字段。缺少必需的中文字段时构建失败。
- 系统名和技术术语保留英文，正文和表头翻译。缩写按原文保留，例如 `20B`、`2-D`。
- 中文用「万」「亿」表示数量级，构建会按数值逐一核对中英文是否一致。

## 4. 更新信号与订阅

- 每张卡显示收录日期、最近核实日期和更新历史，字段见 schema 的 "Update signals" 一节。
- 首页轮播显示最近新增和更新的卡片，数量和时间窗口在 `data/site.yaml` 中配置。
- `/changelog/` 按日期列出全部事件，`/feed.xml` 是 Atom 订阅源。
- 周报归档由 `data/newsletter/*.yaml` 生成，模板是 `templates/newsletter_issue.example.yaml`。
- 订阅框使用 Beehiiv 嵌入，参数在 `data/site.yaml` 中。**测试时不要提交真实邮箱**，否则会产生真实订阅者。

## 5. 校验与测试

`build.py` 本身会做数据校验，以下情况会直接失败：字段缺失或不合法、标签未映射、中文缺失、架构图链接不在来源中。

括号风格检查只告警不失败：卡片名称中不要出现括号；公司、年份和会议放在各自字段里，不写进名称。

测试与 CI 使用 Python 3.12 和 Node 24：

```bash
export SITE_URL=https://jdding.github.io/recarch
python3 build.py
npm install --no-save --prefix /tmp/jt jsdom
python3 tests/carousel_fixture.py /tmp/car-fixtures
python3 tests/faq_validator_test.py
for t in tests/*.test.js; do NODE_PATH=/tmp/jt/node_modules node "$t" || exit 1; done
```

## 6. 日常维护

每周一：

1. `python3 scripts/citations.py` 刷新引用数，支持 `--only id1,id2` 和 `--dry`。
2. `python3 scripts/admission_audit.py` 生成准入报告。边缘卡片的变化只报告，不自动退场。
3. `python3 scripts/refresh.py` 从固定的 feed 和 arXiv 拉取候选，追加到 `review_queue.jsonl`。它只生成待审队列，不会自动发布。

按下方工作路线接续上次检查和候选状态。每周复审 10 张活跃卡，逐张记录保留、升级或待补证据。发现会影响公开结论的明确错误，立即核实并准备双语修正。复审同时核对正式版本与可用链接、线上对照与流量、指标和延迟口径、双语关键字段。原文未披露的字段填未报告。

新增或修改卡片：

1. 读全文，按 schema 写 YAML 和中文翻译，每个数字记下出处页码或表号。
2. 实质升级已有卡片时，在 `updates` 中加一条记录，并更新 `last_verified`。批量字段归位与来源链接维护可在本页集中记录，保留原有证据日期。
3. 跑准入审计、构建和全部测试。
4. 维护者授权后，再按发布流程提交或提 PR，列出关键数字的出处。

轮播、更新日志、订阅源和 sitemap 都会随构建自动更新。

## 7. 部署

推送到 `main` 会触发 `.github/workflows/pages.yml`：用 `SITE_URL=https://jdding.github.io/recarch` 构建，运行测试，然后把 `dist/` 部署到 GitHub Pages。合并后请确认中英文页面都返回 200。

## 8. 安全

抓取脚本只访问写死的 https 主机，跳转后会再次校验；远程 XML 拒绝带实体声明的文档；构建只向 `dist/` 写文件。2026 年 11 月的评审记录见 [`security-review-2026-11.md`](security-review-2026-11.md)。

## 9. 年底工作路线

以 2026-11-25 检查的本地 `main` 起点 `01810fb` 为基线。构建输入有 106 张活跃卡，另有 7 退役、6 并入、6 全文待补草稿和 1 撤稿记录。三个双语专题分别覆盖生成式召回 19 张、长用户序列 12 张、Semantic ID 与物品分词 16 张。预排序与重排分别只有 3 和 9 张，45 张报告了某种线上延迟信息，29 张报告 A/B 流量。延迟字段的测量边界还需逐卡检查。

本地工具包括卡量统计、准入审计、候选抓取、引文刷新和 FAQ 生成。静态 AI 入口、只读 MCP Worker 源码及 Pages 构建工作流均已在仓库中。引文缓存的最近一批日期是 2026-11-03。未找到旧候选队列，既往排期和远程维护任务运行状态待确认。

准入脚本在基线报告 90 张达标、12 张豁免、4 张边缘。边缘卡为 `etsy-unified-embedding-retrieval-2023`、`kuaishou-kuaiformer-2024`、`twitter-x-for-you-2023`、`x-phoenix-for-you-2026`。

Compare 已展示对照、A/B 流量和时长、延迟、吞吐、成本与硬件。专题表展示最多两项线上指标及基线，并附延迟和硬件。HAP、FORGE 和 SORT 的测量范围已在全库复审中核对。

| 周次 | 内容维护交付 | 产品设计交付 | 验收、依赖与延期条件 |
|---|---|---|---|
| 11-23 至 11-29 | 两批新增和升级已发布。原定复审提前展开，完成全库扫描、两张退场、For You 谱系合并及 HIT 补卡。 | 修正 Compare 的推理成本口径，更新长序列专题的关联卡片。 | 新卡以可定位的原文、线上证据、谱系去重与双语构建验收。 |
| 11-30 至 12-06 | 按文末队列复查 10 张。优先补出版全文，并对照正文及图表。 | 检查下列卡片的对照、流量和延迟单位是否能在对比页逐项读懂。 | 更改需有一手证据。版本或数值待核时，保留具体缺项。 |
| 12-07 至 12-13 | 复审下一批 10 张卡，优先检查只读过作者版本的卡。 | 基于已有卡片判断是否具备撰写预排序与重排部署专题的条件。 | 至少三张活跃卡能支持同一个工程问题才起草专题，待证字段保留在对比记录。 |
| 12-14 至 12-20 | 复审 10 张卡，优先检查观察期和 A/B 对照缺项。 | 验收已形成的对比改进或专题的双语链接、移动端阅读和键盘操作。 | 每项升级附原始出处和本地测试。暂缺全文时记录原因和复查条件。 |
| 12-21 至 12-27 | 复审 10 张卡，优先检查线上延迟、吞吐和硬件的测量范围。 | 在现有 Compare 中复核已修正字段的展示。 | 区分离线批测、线上模型推理与端到端请求。 |
| 12-28 至 12-31 | 复审 10 张卡，优先检查版本、来源链接和双语一致性，汇总跨年待办。 | 汇总已验收的产品改动和待决问题。 | 年底记录复审覆盖、可核实的升级和依赖。 |

### 本周计划 · 11-23 至 11-29

2026-11-25 本地完成新增 4/4、升级 1/1。加入本周卡片后，深度系统有 50 张，生成式系统 52 张，古典系统 8 张。

| 名额 | 系统 | 交付和验收 |
|---|---|---|
| 新增 1 · 已验收 | 今日头条 HAP | 依据 WWW 2026 工业赛道论文的作者全文建双语卡。正式版核对待补。 [作者全文 §4.6](https://arxiv.org/html/2603.03770v1#S4.SS6) |
| 新增 2 · 已验收 | Google Discover SDF | 记录两个排序前过滤器，分别标注四周 A/B 抽样、两个月联合保留组和两年投诉监测。 [作者全文 §4.2–4.3](https://arxiv.org/html/2608.15780v1) · [CIKM 程序](https://cikm2026.diag.uniroma1.it/cikm-program/CIKM2026_program.html) |
| 新增 3 · 已验收 | 美团 SIF | 写入历史交互的样本级 token 和 SIF-Mixer。线上结果标出 5% 保留流量、7 天、HyFormer 生产对照及分人群结果。 [作者全文 §4.5](https://arxiv.org/html/2604.15650v3#S4.SS5) · [RecSys 程序](https://recsys.acm.org/recsys26/session-5/) |
| 新增 4 · 已验收 | ByteDance OneTrans | 初代、V2 和 GSR 合成一张谱系卡，主体呈现 GSR。记录一周生产 A/B 和重排、混排延迟口径。初代正式会议长文已记入版本，准入审计按整个谱系核查。 [初代](https://arxiv.org/abs/2510.26104) · [V2](https://arxiv.org/abs/2609.28589) · [GSR 全文 §6.7](https://arxiv.org/html/2611.04720v1#S6.SS7) |
| 升级 1 · 已验收 | YouTube DNN 2016 | 用 Google 托管的会议 PDF 核对出处，区分近期上传视频的线上定性结果、次日保留集的离线结果与训练规模。 [会议论文 PDF](https://static.googleusercontent.com/media/research.google.com/zh-CN//pubs/archive/45530.pdf) |

首批内容已随 `abefb5e` 发布。HAP、SDF 和 SIF 的正式版本待复审。

### 补充候选 · 2026-11-25

卡片证据使用公开原文与官方程序表。先在活跃、并入、退役、草稿、撤稿和引文缓存中查 DOI 与 arXiv ID，再核公司、服务环节及论文本身对系统谱系的描述。

| 状态 | 候选 | 证据及下一步 |
|---|---|---|
| 已发布 | 快手 NAR4Rec | KDD 2024 长文。并行计算输出位置分布，与 GloRank 的逐步生成形成工程对照。生产测试以 Edge-rerank 为对照，实验组占 20%，作者报告全量上线。 [作者全文 §5.3](https://arxiv.org/html/2402.06871v6#S5.SS3) |
| 本轮纳入 | 腾讯 HIT | CIKM 2025 Applied Research 长文，补可缓存双塔的广告预排序。五天 A/B 对照 MVKE，共用下游，比较收入规模与投放回报。 [作者全文 §5.5](https://arxiv.org/html/2505.19849v2#S5.SS5) · [CIKM 录用程序](https://www.cikm2025.org/program/accepted-papers) |
| 候选 | 淘宝 ICE/JBM | 首页重排评估器，固定生成器，报告 14 天生产 A/B 和全量部署。重排已有 10 张，本轮新增名额用于广告预排序。下轮从已有淘宝重排卡的产品入口和替代关系判断独立收录价值。 [ICE 作者全文](https://arxiv.org/html/2611.07591v1) |
| 已发布 | Amazon COSMO | 基于 SIGMOD 工业赛道正式全文，记录缓存式知识服务。线上证据限于受试美国流量中的搜索导航功能。 [Amazon 官方全文](https://assets.amazon.science/19/5d/bde30d0d4019be6421e79e50cda9/cosmo-paper.pdf) |
| 已补正式记录和版本历史 | GloRank、淘宝 SORT-Gen | GloRank 原卡补正式标题、DOI 及作者团队对快手部署的确认。SORT-Gen 并入 NextGen 原卡版本历史。NextGen 全文确认它是同一团队已部署的秒杀对照，SORT-Gen 原论文实验在百亿补贴。 [GloRank 会议程序](https://cikm2026.diag.uniroma1.it/cikm-program/CIKM2026_program.html) · [SORT-Gen 正式记录](https://doi.org/10.1145/3726302.3731935) |
| 等合格长版或适用豁免 | 淘宝 TARQ | 量化近似目标注意力，补预排序的效率取舍。论文报告淘宝生产 A/B 和全量部署，已查到的作者版共 5 页，暂缓独立收录。 [作者全文](https://arxiv.org/pdf/2509.16931v3) |
| 有全文和工业部署证据 | ConAlign | 快手短视频排序有论文全文和生产 A/B。深度卡名额有限，留在候选队列。 [作者全文 §4.4](https://arxiv.org/html/2607.24092v1#S4.SS4) |
| 待补上线读数 | CascadeRec | Workday 作者全文报告企业租户上的生产 A/B。推理成本约降 10%，为整组改动的代币成本对比。业务指标仍在累积，时延只给定性结论，等最终读数再排卡。 [作者全文 §4](https://arxiv.org/html/2611.08566v1#S4) |
| 待核持续上线 | PRM | RecSys 2019 正式全文有未具名电商站点在线 A/B，对照是 DNN 学习排序模型；持续上线状态待核。若补足证据，进入季度补课。 [正式全文 §5.6 与表 6](https://yongfeng.me/attach/pei-recsys2019.pdf) |
| 已覆盖 | TGR | 现有 `tencent-tgr-2026` 卡已使用同一 arXiv ID。按原卡追踪后续版本。 [原论文](https://arxiv.org/abs/2609.00986) |
| 不入收录范围 | PEAR | WWW 2022 Companion 短文，正式版共 5 页。本轮没有找到合格长文。 [ACM 记录](https://doi.org/10.1145/3487553.3524208) |

### 首周本地验收

本周结束时，中英文各构建 110 张系统卡。准入脚本报告 94 张达标、12 张豁免、4 张边缘，本周五张卡全部达标。Python 3.12 与 Node 24 下，轮播数据、FAQ 校验和全部 15 项 JavaScript 测试通过。更新后的 FAQ 和评测条目待人工审阅，原有评测编号保留。三个既有专题均有中英文构建页，Semantic ID 专题的线上部署待确认。

### 年底发布判断与首轮复审

已发布基线 110 张中，44 张覆盖召回、5 张覆盖预排序、10 张覆盖重排。多阶段卡可计入多个环节。本地批次保留四张召回卡，再加入 NAR4Rec 重排和 COSMO 搜索知识服务，构建后共 116 张。每周复审继续从已发布基线开始。

| 发布评审 | 本地候选 | 相对现有覆盖的增量 |
|---|---|---|
| 纳入本地批次 | Spotify GLIDE、Shopify SID-LLM | GLIDE 补播客发现和长短期兴趣结合。SID-LLM 可与 PinRec 比较跨搜索和推荐的生产设计，搜索和首页共用商品语义 ID，各自采用多 token 预测和自回归召回。 [GLIDE §5.3](https://arxiv.org/html/2603.17540v1#S5.SS3) · [SID-LLM §7](https://arxiv.org/html/2611.08804v1#S7) |
| 纳入本地批次 | 百度 ICEGR、Alibaba International ReSID | ICEGR 补候选直达曝光及其服务吞吐。ReSID 补广告长尾可达性，给出替换 TIGER 式召回的对照、长尾曝光指标和作者实现。 [ICEGR §4.5–4.6](https://arxiv.org/html/2608.29652v3#S4.SS5) · [ReSID §5.7](https://arxiv.org/html/2611.16404v1#S5.SS7) |
| 纳入本地批次 | 快手 NAR4Rec、Amazon COSMO | 补非自回归重排和搜索导航的知识服务。 |
| 双语草稿顺延 | Alibaba International TriGen、Meta G2Rec | 双语稿移至 `data/drafts/`。Related Pins 和 PinRec 已能提供种子物品触发的参照。G2Rec 的产品场景、线上对照及生产环节待补证据。 [TriGen §5.5](https://arxiv.org/html/2611.16395v1#S5.SS5) · [G2Rec §5.3](https://arxiv.org/html/2606.20554v1#S5.SS3) |

以上批次随 `da6a386` 发布。线上中英文各 116 张卡。NAR4Rec、GLIDE、GloRank 和 CQ-SID 的线上数字已核对作者全文，ACM 托管全文待核。

### 全库复审 · 2026-11-25

逐卡检查 116 张线上卡的状态、DOI、arXiv ID、正式版本标记、线上证据和对照字段，并核对可疑数字和同一产品谱系。批量读取公开全文、官方文档或代码后，再用可取得的会议全文核对重点案例。未能重读出版全文的卡继续保留原有版本标记，当前有 42 张标记为出版全文待核。

| 复审结论 | 变更 |
|---|---|
| 退场两张 | Etsy 的论文来源层级未达标，KuaiFormer 的 arXiv 观察期已过。旧 YAML 保留，双语长用户序列专题从十二张减到十一张。 |
| 两张合一 | X For You 保留 2023 年 Twitter 版本与 Phoenix 版本历史。新版按向量召回与行为打分列在深度架构中，语义 ID 用于表示帖子。官方代码有架构和训练服务说明，未披露 A/B。 [Phoenix 官方代码快照](https://github.com/xai-org/x-algorithm/blob/52d45989090e63992ba04e4f6cfccd73bf8cc05c/phoenix/README.md) |
| 新增一张 | 腾讯 HIT 与现库相邻的召回、广告排序卡解决的是不同阶段的问题。预排序比较保持双塔可缓存时如何补回交互信息。作者全文第 5.5 节与表 4 记录五天 A/B，GMV +1.66%、ROI +1.55%。 [HIT 作者全文](https://arxiv.org/html/2505.19849v2#S5.SS5) |
| 核对九份正式全文 | Airbnb 搜索 DNN、ESMM、Facebook Search EBR、快手 OneLoc、Meta VLM、MIND、TransAct V2、SIM、YouTube REINFORCE。TransAct V2 补三周与每组样本量，SIM 补日期和 MIMN 对照，YouTube 分开随机策略与 top-K 两项试验，ESMM 标明部署证据指向 BASE。 |
| 修正可比性 | Airbnb 相似房源轮播的整体 CTR 为 +21%，无日期子集为 +20%。16 张卡移出了推理成本栏里的结构、配置或效率描述，保留在部署说明中。HAP 的 CPU 用量、FORGE 的异步缓存完成时间和 SORT 四场景相对延迟各自保留测量口径。 |

活跃卡现为 114 张，其中古典 8、深度 50、生成式 56。准入审计为 99 张达标、15 张按既有规则豁免。双语首页轮播满是更新时，若最后一张同一天有新增，留一位给新增。证据更新后重新生成的问答按现有流程等待人工复核，问答评测保留已有条目的编号。

下次每周轮到的 10 张依次是 HAP、Google Discover SDF、美团 SIF、淘宝 CQ-SID、腾讯 HIT、快手 GloRank、Meta Unity、Meta Lattice、阿里 URM、Spotify GLIDE。先核正式全文与作者版差异，检查 Unity 的 Pollen 实验和 Lattice 的指标定义。ICE/JBM 的独立性可并行判断，容量按实际复审结果计算。

### 专题开发 · 2026-11-26

- [推荐算法的递归自我改进](../data/i18n/zh/topics/recommendation-rsi.yaml) 以 YouTube 和快手 AgentX 的模型迭代流程为主，Meta Shape Your Feed 用作反馈对齐的边界参照。正文比较试验筛选、完整重训、上线验收和下一轮证据，延伸阅读收录两篇同名 RecRSI 及相关基准。
- [Agent 如何使用推荐能力](../data/i18n/zh/topics/agentic-recommendation.yaml) 对比 RecBot 的指令驱动工具链、Meta 的在线重排和快手 EvoRec 的近线补充召回。评测阅读分别覆盖多轮约束、兴趣变化和集合效用。
- 两个专题共用现有双语专题模板。新增书目链接仅用于延伸阅读，专题表里的部署数字继续取自系统卡。YouTube 与 RecBot 正式出版全文待核，两张卡的线上数字均指向已经查阅的公开作者全文。

### 两个专题的文献复扫 · 2026-11-26

公开资料窗口为 2023 年 1 月至 2026 年 11 月 26 日。先通过 Zotero KB 的实时只读查询发现候选，再查 arXiv、RecSys 与 KDD 2026 会议清单、ACL Anthology、NeurIPS、PMLR、OpenReview 和官方工程资料。沿两篇综述与重点工作回溯引文。下表的命中数含预印本和正式版重复、正文提及及无关命中，不能视为论文总数。

| 专题 | Zotero 实际查询串 | 返回 |
|---|---|---|
| [推荐算法的 RSI](../data/i18n/zh/topics/recommendation-rsi.yaml) | `recursive self-improvement recommender systems`、`self-evolving recommender systems`、`automated recommender model optimization`、`agent recommender architecture evolution`、`agent iterative recommendation experiments`、`recommender systems research agent`、`2609.01622`、`2607.29241`、`NOVA A Verification-Aware Agent Harness`、`10.1145/3773078.3831898`、`2606.27243`、`推荐系统 自我进化` | 12 次，85 条 |
| [Agent 如何使用推荐能力](../data/i18n/zh/topics/agentic-recommendation.yaml) | `2609.30297`、`agentic recommender systems`、`interactive recommendation agent`、`agentic recommender systems benchmark`、`agent tool use recommendation catalog`、`conversational recommendation retrieval agent`、`agent uses recommendation tools user tasks`、`multi-turn recommendation constraints`、`shopping agent product recommendation`、`Agent 推荐工具`、`对话推荐 召回 排序` | 11 次，101 条 |

公开检索用同类关键词增加 `online A/B`、`production` 或评测关键词和会议域名。RSI 从[评估综述](https://www.preprints.org/manuscript/202610.2336/v1)、[RecHarness](https://arxiv.org/html/2607.29241v2)和 [NOVA](https://arxiv.org/html/2606.27243v3)追踪被引用工作，覆盖试验预算、代码验证、代理指标与真实流量。Agent 专题从 [Lin 等的综述](https://arxiv.org/abs/2607.04433)、[τ-Rec](https://taubench.com/community/tau-rec.html)与 RecSys 工业和资源赛道条目补查，覆盖意图澄清、工具选择、目录候选和任务验收。Zotero 精确标识找到 RecEvolve、RecHarness 和 Spotify。NOVA 的标题和 arXiv ID 查询只返回关联命中，最终用公开作者全文核证。

同一研究按 DOI、arXiv ID 和标题归并。同一系统的版本保留在原卡。专题正文列出工业系统，延伸阅读说明每份资料回答的问题，资料范围概括覆盖的时间和主题。Google RecEvolve 的产品未披露，暂未发现其是 YouTube 排序研发卡的同一实现。RecHarness 实验改变广告排序器的商业序列编码，AgentX 卡描述跨业务的研发谱系，作者资料分别描述两套方法。

| 优先复核 | 本地处理与证据 |
|---|---|
| RecEvolve | 新卡。RecSys 工业赛道书目第 1437–1442 页，作者稿正文延续到最后一页，按约六页规则审查。第 5.7 节和表 2 比较入选双塔与现网模型。论文未披露产品、时长及流量。 [正式书目](https://doi.org/10.1145/3773078.3831898) · [作者全文](https://arxiv.org/html/2609.01622v1#S5.SS7) |
| RecHarness | 新卡。公司署名的 arXiv 作者版在观察期内，v2 第 3.5 节和表 4 报告 7 天、覆盖 10% 生产流量的短视频广告实验。对照配置和组间分流未披露。 [作者全文](https://arxiv.org/html/2607.29241v2#S3.SS5) |
| NOVA | 新卡。采用 v3 第 5.7 节与表 4 的 6 天、5% 流量、按用户随机口径。NOVA 用于生产研发，论文把入选排序改动的全量推广列为后续计划。arXiv 作者版处于观察期。 [作者全文](https://arxiv.org/html/2606.27243v3#S5.SS7) |
| Spotify | 新卡。RecSys 工业赛道正式书目共 10 页。第 4.3 节用仅支持调整当前会话的旧体验作对照。两周 A/B 触达约 1500 万用户，效果对应完整体验。 [正式书目](https://doi.org/10.1145/3773078.3831910) · [作者全文](https://arxiv.org/html/2609.30297v1#S4.SS3) |

RSI 含五张正文系统卡和十篇延伸阅读。Meta Shape Your Feed 放在 RSI 的反馈对齐相关阅读中，并继续作为 Agent 专题案例。Agent 专题含四张正文系统卡和十一篇延伸阅读。候选的复审理由可回查 `3792c3d` 的专题数据。RecEvolve 和 Spotify 的指标已核作者全文，ACM 托管的出版全文待核。维护者批准两个专题与四张新卡同批发布，本批保留 122 张活跃卡。

本地双语构建各有 122 张活跃卡。准入审计为 103 张达标、19 张豁免通过，FAQ 校验和 15 项 JavaScript 测试通过。已访问 18 个本机预览地址，并用桌面和窄屏浏览器核对专题筛选跳转。

### 端云协同推荐专题 · 2026-11-26

以候选从哪里来、手机能依据哪些即时信号决策为主线。首轮用本地书目索引做实时只读查询，再核对正式书目和作者全文。复审时实时索引返回过期，新增证据来自公开原文。端侧重排以可用的云候选为起点，端侧补召以同候选预算、同排序器、同资格约束下的增量为验收对象。弱网缓存替换与端侧意图云检索各自保留原论文的任务边界。

| 去留 | 公开证据与范围 |
|---|---|
| EdgeRec 入正文 | 手机淘宝用云候选和查表所得嵌入在端上重排未曝光项。第 4.2 节分开给出业务 A/B 与系统响应和行为感知延迟。 [CIKM 论文](https://doi.org/10.1145/3340531.3412700) · [作者全文](https://arxiv.org/pdf/2005.08416) |
| 快手端侧短视频重排入正文 | 云分是端模型输入。表 6 的一周 A/B 比较现网、逐点贪心和上下文束搜索，表 7 报告端模型与搜索平均耗时。 [CIKM 论文](https://doi.org/10.1145/3511808.3557065) · [作者全文](https://arxiv.org/pdf/2208.09577v2) |
| Kwai Playback 入正文 | 弱网风险触发从既有云端补充缓存选替代视频。表 5 给出整体和弱网口径，采用实验最后七天均值。与沉浸式下一条视频重排分属不同入口与干预。两篇作者资料分别描述两个系统。 [CIKM 论文](https://doi.org/10.1145/3627673.3680076) · [作者全文](https://arxiv.org/pdf/2410.05863) |
| RecGPT-Mobile 入正文 | 复核补找到同一团队的 36 页 V2 技术报告，按系统谱系合为一张卡。SIGIR 五页版第 4.2 节报告生产 A/B。卡片主体采用 V2，表 8 的曝光 PV 份额与用户覆盖是线上绝对指标，图 12 是单独的查询服务测试。V2 的随机流量业务收益未披露。 [SIGIR 作者全文](https://arxiv.org/html/2605.04726#S4.SS2) · [V2 技术报告](https://arxiv.org/html/2608.24295#S10.SS4) |
| Meta Controller 和 DIR 放延伸阅读 | Meta Controller 使用包括支付宝干预日志在内的数据集比较调度策略。DIR 由华为与高校团队提出，给出 Celia Suggestions 等日志上的比较和推理耗时。两份原文尚未核到所提系统本身的部署 A/B。 [Meta Controller](https://arxiv.org/html/2207.03066) · [DIR 作者全文](https://wnzhang.net/papers/2023-kdd-dir.pdf) |

LSC4Rec、Shaver 和 OD-LLM 提供数据集实验或推理测量，适合对照云端刷新、端侧嵌入裁剪和模型压缩。相关综述跨多个系统，Spotify 公告说明账号授权及产品接入。七份资料保留在延伸阅读。

正文包含四个生产案例。RecGPT-Mobile 用端侧查询触发云检索。要验证端侧补召，仍需核实设备本地能获得、能展示和能打分的额外物品。各专题的候选复审内容已从页面移除，读者可以通过「资料范围」了解取材范围。

本地中英文各构建 126 张活跃卡，准入审计为 107 张达标、19 张豁免通过。FAQ、轮播和 15 套 JavaScript 测试通过。逐页核对六个专题及 RecGPT-Mobile 卡片的中英文预览。

本批发布包含端云协同专题、四张新卡及其他专题的页面精简。中英文首页的「本周动态」提供端云协同专题入口。同日发布的站点公告按录入先后显示最新一条。

### 后续每周记录

在同一维护会话从本表继续，记录本地变更、来源、构建与测试结论、延期原因和下周首项。公开数据用原文链接和章节、图表定位。内部检索材料留在本机。需要提交、推送、开 PR、发布、登录云端或使用付费服务时，另行取得维护者授权。

#### 10 卡复审 · 2026-11-26

沿用 11 月 25 日全库复审排出的 10 张卡，优先核查正式书目、线上对照和容量、延迟、吞吐的测量范围。实时书目索引本轮无法完成当前版本探测，复审依据为九份公开作者全文、正式书目和官方资料。ACM 托管 PDF 本轮未能直读，出版全文核对状态沿用已有记录。

| 系统 | 本地结论 | 核对依据 |
|---|---|---|
| HAP | 升级。把路由消融中 HAP 的 203 ms 和单一大模型的 225 ms 并列，并补训练 CPU 核时。正式上线 A/B 的延迟说明单独保留。 | [作者全文 §4.5.1、表 5 和 §4.6](https://arxiv.org/html/2603.03770v1) · [WWW 工业赛道名单](https://www2026.thewebconf.org/accepted/industry.html) |
| Google Discover SDF | 升级。写清过时占比差的减法方向和人工标注口径，另列两个月保留组的置信区间。 | [作者全文 §4.2、公式 8 和表 3](https://arxiv.org/html/2608.15780v1) |
| 美团 SIF | 升级。补离线实验使用的 8 块 A100 80 GB，线上服务硬件仍待披露。 | [作者全文 §4.1 和 §4.5](https://arxiv.org/html/2604.15650v3) |
| 淘宝 CQ-SID | 升级。约 40 ms 和 8 块 GPU 共承载的超过 200 QPS 都归到生成式召回服务。 | [作者全文 §4.5](https://arxiv.org/html/2605.14434v2) |
| 腾讯 HIT | 升级。把表格与正文的 GMV 差异放到结果旁。表 4、摘要、结论均为 GMV +1.66%、ROI +1.55%。图 6 是模型响应与成功率的基准。 | [作者全文 §5.5、表 4 和图 6](https://arxiv.org/html/2505.19849v2#S5.SS5) |
| 快手 GloRank | 保留。作者稿确认 14 天、试验组 7.8% 流量和等量 GoalRank 对照。作者实验室的部署说明与论文试验覆盖各自保留来源。 | [作者全文 §4.10 和表 4](https://arxiv.org/html/2604.25291v1) · [作者实验室](https://aml-cityu.github.io/publications/) |
| Meta Unity | 保留。已确认正式书目及公开仓的 DCNv2、WuKong 基准实验范围。Pollen 线上精确数字仍引用此前核过的定稿，本轮未重读该 PDF。 | [KDD 正式书目](https://doi.org/10.1145/3770855.3818505) · [Meta 官方代码](https://github.com/facebookresearch/unity) |
| Meta Lattice | 升级。明确对照按领域和目标分别建模，标明广告质量与转化口径。20% 为电力容量节省，另列 KTAP 缓存命中条件下的损失比较。 | [作者新版 §3.4、§4.5 和 §5](https://arxiv.org/html/2512.09200v2) · [Meta 2023 年公告](https://ai.meta.com/blog/ai-ads-performance-efficiency-meta-lattice/) |
| 阿里 URM | 升级。区分 10 分钟候选刷新窗口、模型 p99 基准和线上广告实验。A/B 对照配置及采用的骨干均标为未披露。 | [作者全文 §4、§5.5 和附录 B.4 表 7](https://arxiv.org/html/2502.03041v2) |
| Spotify GLIDE | 升级。补语义 ID 冲突处理与同延迟目标下最高 8 倍的相对吞吐，绝对 QPS 保留为未披露。 | [作者全文 §4.4 和 §5.3](https://arxiv.org/html/2603.17540v1) · [Spotify 官方说明](https://research.atspotify.com/2026/8/from-models-to-products-llms-for-recommendation-at-spotify-scale) |

本轮共升级 8 张、保留 2 张。受影响的问答评测条目沿用已有编号，更新后的 Meta Lattice FAQ 回到待审。HISAC、NAR4Rec 和 OneMall 已纳入随后的全库复审。

本地中英文各构建 126 张活跃卡，准入审计为 107 张达标、19 张豁免通过。FAQ、轮播和 15 套 JavaScript 测试通过。核对 26 个本机预览地址，覆盖 10 张卡、双语切换和对比页。

#### 全量线上内容复审 · 2026-11-26

已对 126 张活跃系统卡和 6 个专题集中复审。逐卡证据、修订理由和还需重读全文的字段记录在[全库复审记录](content-review-2026-11-26.md)。本次本地修订 22 张卡和 2 个专题，上一轮 8 张卡的更新并入同一个预览。下次接续时优先找 Unity、DPGR 和 NextGen 的可访问定稿，按复审记录核完余下字段。

中英文各构建 126 张活跃卡。准入审计为 107 张达标、19 张豁免通过。FAQ 校验、轮播和 15 套 JavaScript 测试通过。通过本机 HTTP 核对 270 条双语页面地址和两套对比数据。受影响的 15 份 FAQ 已同步到新内容，7 份此前已审的 FAQ 回到待审，评测条目继续沿用原编号。
