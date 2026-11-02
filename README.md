# RecArch：工业推荐系统架构图谱

**[jdding.github.io/recarch](https://jdding.github.io/recarch/)** · [English](https://jdding.github.io/recarch/en/) · [订阅周报](https://recarch.beehiiv.com/subscribe) · [反馈与收录建议](https://github.com/jdding/recarch/issues/new/choose)

RecArch 收录已在工业界上线的推荐、搜索与排序系统，每个系统整理成一张结构化卡片，帮助做架构选型的工程师快速了解：这个系统解决什么问题，怎么做的，在哪里上线，效果和代价各是多少。

> RecArch is a bilingual, sourced map of production recommender, search and ranking architectures. Each system gets one structured card with its deployment scene, A/B setup, baseline, online gains, and training and serving cost, all taken from the full text of its sources. Chinese is the default; the English site lives at `/en/`.

## 每张卡片包含什么

- **核心思路**：一句话 TL;DR 和简要说明，部分卡片附我们自己重绘的简化架构图。
- **上线证据**：上线场景、流量和 A/B 时长、对照基线、线上指标涨幅。
- **部署成本**：训练算力、推理延迟和成本。
- **元数据**：公司、年份、会议、范式与阶段标签、证据等级、引用数、官方代码情况。
- **版本历史**：多版本系统只保留一张卡，展示最新版本，旧版本列出名称和论文链接。

站点还提供筛选与时间线视图、系统对比、专题对比页（如长序列建模、生成式召回）、更新日志和 Atom 订阅。

## 内容原则

1. **只基于全文**：卡片必须读过来源全文，正式发表版本优先。只读过摘要的条目留在草稿区，不发布。
2. **数字有出处**：所有数字都来自论文或官方技术文章原文。原文没有报告的写「未报告」，不估算，翻译也不新增数字。
3. **只发布解读**：仓库和站点只包含我们的结构化解读与重绘图，不存放、不分发论文 PDF 或原文。
4. **准入有标准**：收录、排期、复查与退出规则见 [`docs/admission.md`](docs/admission.md)。不再满足标准的卡片不在站点展示，数据文件保留在仓库中。

发现错误或想推荐系统，请通过 [GitHub Issues](https://github.com/jdding/recarch/issues/new/choose) 提交，模板分「纠错」和「申请收录」两类。

## 本地构建

需要 Python 3 和 PyYAML。

```bash
pip install -r requirements.txt
SITE_URL=https://jdding.github.io/recarch python3 build.py   # 生成 dist/，同时校验全部卡片
cd dist && python3 -m http.server 8080
```

当前卡片数量由脚本统计，不在文档中手写：`python3 scripts/stats.py`。

## 仓库结构

| 路径 | 内容 |
|---|---|
| `data/systems/` | 每个系统一个 YAML 卡片，字段规范见 [`schema/schema.md`](schema/schema.md) |
| `data/i18n/` | 中文翻译与界面文案 |
| `data/topics/` | 专题对比页 |
| `data/diagrams/` | 重绘架构图 |
| `data/drafts/` | 尚未读到全文的草稿，不参与构建 |
| `data/citations.json` | 引用数，脚本生成 |
| `build.py` | 静态站点生成器，含数据校验 |
| `scripts/` | 引用数刷新、候选发现、准入审计、统计 |
| `tests/` | 页面与数据测试 |
| `docs/` | 准入标准、开发说明、安全评审记录 |

## 开发与维护

数据模型、构建校验、双语规则、测试命令、每周维护流程和部署方式见 [`docs/development.md`](docs/development.md)。

推送到 `main` 后，GitHub Actions 会自动构建、跑测试并部署到 GitHub Pages。

## 许可

- **代码**：`build.py`、`scripts/`、`templates/`、`static/`、`tests/` 等代码以 [MIT](LICENSE) 许可发布。
- **内容**：`data/` 下的卡片、翻译、专题与重绘架构图，以及站点上由它们生成的文字，以 [CC BY 4.0](LICENSE-CONTENT) 许可发布。转载或改编请注明出处「RecArch（jdding.github.io/recarch）」并附原链接。
- 卡片引用的论文、技术博客及其中的图表、数据，版权归原作者和原机构所有，不在上述许可范围内。公司名称仅用于标识系统来源。

© 2026 Ding Jiandong
