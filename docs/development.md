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

按下方工作路线接续上次检查和候选状态。周一是维护节奏，常规目标为每周新增 4 张、升级 1 张。实际交付量由准入证据和审查容量决定。

新增或修改卡片：

1. 读全文，按 schema 写 YAML 和中文翻译，每个数字记下出处页码或表号。
2. 修改已有卡片时，在 `updates` 中加一条记录，并更新 `last_verified`。
3. 跑准入审计、构建和全部测试。
4. 开分支提 PR，在描述中列出关键数字的出处，确认后合并。

轮播、更新日志、订阅源和 sitemap 都会随构建自动更新。

## 7. 部署

推送到 `main` 会触发 `.github/workflows/pages.yml`：用 `SITE_URL=https://jdding.github.io/recarch` 构建，运行测试，然后把 `dist/` 部署到 GitHub Pages。合并后请确认中英文页面都返回 200。

## 8. 安全

抓取脚本只访问写死的 https 主机，跳转后会再次校验；远程 XML 拒绝带实体声明的文档；构建只向 `dist/` 写文件。2026 年 11 月的评审记录见 [`security-review-2026-11.md`](security-review-2026-11.md)。

## 9. 四周工作路线

以 2026-11-25 检查的本地 `main` 起点 `01810fb` 为基线。构建输入有 106 张活跃卡，另有 7 退役、6 并入、6 全文待补草稿和 1 撤稿记录。三个双语专题分别覆盖生成式召回 19 张、长用户序列 12 张、Semantic ID 与物品分词 16 张。预排序与重排分别只有 3 和 9 张，45 张报告了某种线上延迟信息，29 张报告 A/B 流量。延迟字段的测量边界还需逐卡检查。

本地工具包括卡量统计、准入审计、候选抓取、引文刷新和 FAQ 生成。静态 AI 入口、只读 MCP Worker 源码及 Pages 构建工作流均已在仓库中。引文缓存的最近一批日期是 2026-11-03。未找到旧候选队列，既往排期和远程维护任务运行状态待确认。

准入脚本在基线报告 90 张达标、12 张豁免、4 张边缘。边缘卡为 `etsy-unified-embedding-retrieval-2023`、`kuaishou-kuaiformer-2024`、`twitter-x-for-you-2023`、`x-phoenix-for-you-2026`。

Compare 已展示对照、A/B 流量和时长、延迟、吞吐、成本与硬件。专题表展示最多两项线上指标及基线，并附延迟和硬件。下一轮用 HAP、FORGE 和 SORT 检查读者能否分辨 CPU 用量、异步缓存时间与跨场景服务延迟的测量口径。

| 周次 | 内容维护交付 | 产品设计交付 | 验收、依赖与延期条件 |
|---|---|---|---|
| 11-23 至 11-29 | 已在本地完成 HAP、Google Discover SDF、美团 SIF、OneTrans 四张新增卡和 YouTube DNN 升级。 | 盘点既有 Compare 与专题的部署字段，选定上线条件为下一轮设计重点。 | DOI、arXiv 与谱系去重，核对原文中的在线对照和生产条件，双语构建与测试通过。HAP、SDF 和 SIF 的 ACM 托管全文另行核对。 |
| 11-30 至 12-06 | 接续本周延期项并复核 CascadeRec 最终 A/B 读数。复查 HAP 正式版或挑一张边缘卡核实来源。 | 用三张卡审查 Compare 的部署口径，记录一个可修复的问题。 | 每条证据能定位到来源或标明未报告。谱系和准入无法证实的候选留在队列，比较审查可独立交付。 |
| 12-07 至 12-13 | 依据上周通过的证据整理一批可复审的卡片新增或升级，同时核对生成式和深度卡量。 | 用现有双语模板起草一个部署取舍专题，先试预排序与重排的路由选择。 | 至少三张活跃卡能支撑工程决策，数据从卡片生成。若证据不足以支持专题，保留比较问题和待补字段。 |
| 12-14 至 12-20 | 复查观察期及四张边缘卡，记录保留、升级或待判理由。 | 验收通过的对比改进或专题在两种语言下的链接、移动端阅读和键盘操作。 | 每项改动有原始出处和本地测试结果。缺正式全文或页面证据时记录原因并滚入下周。 |

### 本周计划 · 11-23 至 11-29

2026-11-25 本地完成新增 4/4、升级 1/1。加入本周卡片后，深度系统有 50 张，生成式系统 52 张，古典系统 8 张。

| 名额 | 系统 | 交付和验收 |
|---|---|---|
| 新增 1 · 已验收 | 今日头条 HAP | 依据 WWW 2026 工业赛道论文的作者全文建双语卡。正式版核对待补。 [作者全文 §4.6](https://arxiv.org/html/2603.03770v1#S4.SS6) |
| 新增 2 · 已验收 | Google Discover SDF | 记录两个排序前过滤器，分别标注四周 A/B 抽样、两个月联合保留组和两年投诉监测。 [作者全文 §4.2–4.3](https://arxiv.org/html/2608.15780v1) · [CIKM 程序](https://cikm2026.diag.uniroma1.it/cikm-program/CIKM2026_program.html) |
| 新增 3 · 已验收 | 美团 SIF | 写入历史交互的样本级 token 和 SIF-Mixer。线上结果标出 5% 保留流量、7 天、HyFormer 生产对照及分人群结果。 [作者全文 §4.5](https://arxiv.org/html/2604.15650v3#S4.SS5) · [RecSys 程序](https://recsys.acm.org/recsys26/session-5/) |
| 新增 4 · 已验收 | ByteDance OneTrans | 初代、V2 和 GSR 合成一张谱系卡，主体呈现 GSR。记录一周生产 A/B 和重排、混排延迟口径。初代正式会议长文已记入版本，准入审计按整个谱系核查。 [初代](https://arxiv.org/abs/2510.26104) · [V2](https://arxiv.org/abs/2609.28589) · [GSR 全文 §6.7](https://arxiv.org/html/2611.04720v1#S6.SS7) |
| 升级 1 · 已验收 | YouTube DNN 2016 | 用 Google 托管的会议 PDF 核对出处，区分近期上传视频的线上定性结果、次日保留集的离线结果与训练规模。 [会议论文 PDF](https://static.googleusercontent.com/media/research.google.com/zh-CN//pubs/archive/45530.pdf) |

本周卡片已进入本地预览。下轮复查从 HAP 的正式版本与 Compare 部署口径开始。

### 补充候选 · 2026-11-25

卡片证据使用公开原文与官方程序表。先在活跃、并入、退役、草稿、撤稿和引文缓存中查 DOI 与 arXiv ID，再核公司、服务环节及论文本身对系统谱系的描述。

| 状态 | 候选 | 证据及下一步 |
|---|---|---|
| 有全文和工业部署证据 | ConAlign | 快手短视频排序有论文全文和生产 A/B。深度卡名额有限，留在候选队列。 [作者全文 §4.4](https://arxiv.org/html/2607.24092v1#S4.SS4) |
| 待补上线读数 | CascadeRec | Workday 作者全文报告企业租户上的生产 A/B。推理成本约降 10%，为整组改动的代币成本对比。业务指标仍在累积，时延只给定性结论，等最终读数再排卡。 [作者全文 §4](https://arxiv.org/html/2611.08566v1#S4) |
| 待核持续上线 | PRM | RecSys 2019 正式全文有未具名电商站点在线 A/B，对照是 DNN 学习排序模型；持续上线状态待核。若补足证据，进入季度补课。 [正式全文 §5.6 与表 6](https://yongfeng.me/attach/pei-recsys2019.pdf) |
| 已覆盖 | TGR | 现有 `tencent-tgr-2026` 卡已使用同一 arXiv ID。按原卡追踪后续版本。 [原论文](https://arxiv.org/abs/2609.00986) |
| 不入收录范围 | PEAR | WWW 2022 Companion 短文，正式版共 5 页。本轮没有找到合格长文。 [ACM 记录](https://doi.org/10.1145/3487553.3524208) |

### 首周本地验收

本周结束时，中英文各构建 110 张系统卡。准入脚本报告 94 张达标、12 张豁免、4 张边缘，本周五张卡全部达标。Python 3.12 与 Node 24 下，轮播数据、FAQ 校验和全部 15 项 JavaScript 测试通过。更新后的 FAQ 和评测条目待人工审阅，原有评测编号保留。三个既有专题均有中英文构建页，Semantic ID 专题的线上部署待确认。

### 后续每周记录

在同一维护会话从本表继续，记录本地变更、来源、构建与测试结论、延期原因和下周首项。公开数据用原文链接和章节、图表定位。内部检索材料留在本机。需要提交、推送、开 PR、发布、登录云端或使用付费服务时，另行取得维护者授权。
