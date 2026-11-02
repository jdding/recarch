# RecArch 开发与维护说明

本文档面向维护者，说明数据模型、构建校验、双语规则、测试、日常维护和部署。卡片字段的完整定义以 [`schema/schema.md`](../schema/schema.md) 为准，收录与排期规则以 [`admission.md`](admission.md) 为准。

## 1. 架构

RecArch 是纯静态站点，没有后端。`build.py` 读取 `data/` 下的 YAML，校验后生成 `dist/`，包括中英文两套页面、`sitemap.xml`、`feed.xml` 和 `robots.txt`。

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

测试与 CI 保持一致：

```bash
export SITE_URL=https://jdding.github.io/recarch
python3 build.py
npm install --no-save --prefix /tmp/jt jsdom
python3 tests/carousel_fixture.py /tmp/car-fixtures
for t in tests/*.test.js; do NODE_PATH=/tmp/jt/node_modules node "$t" || echo "FAIL $t"; done
```

## 6. 日常维护

每周一：

1. `python3 scripts/citations.py` 刷新引用数，支持 `--only id1,id2` 和 `--dry`。
2. `python3 scripts/admission_audit.py` 生成准入报告。边缘卡片的变化只报告，不自动退场。
3. `python3 scripts/refresh.py` 从固定的 feed 和 arXiv 拉取候选，追加到 `review_queue.jsonl`。它只生成待审队列，不会自动发布。

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
