# 安全复查 2026-11-02

基线：`479e309`（main，Weekly citations refresh）。没有 Mimosa 的明细报告，下面按它惯用的 high 规则族（SSRF、路径穿越、XML 外部实体 / 实体展开、命令执行、`document.write`）把 `scripts/refresh.py`、`scripts/citations.py`、`build.py`、`scripts/make_assets.py`、`tests/` 里的调用点逐个复原。行号是 **479e309 上的行**。

这是本地跑的静态站生成器：卡片 YAML 由维护者提交，`build.py` 不访问网络，刷新脚本的 feed URL 是写死的。判定标准是「这个调用点在这个用法下会不会被不可信输入利用」，不是「扫描器有没有响」。

## 计数

| | 数量 |
|---|---|
| 复原的 high 调用点 | 41 |
| 真实风险 | 4 |
| 误报 | 37 |
| 已改（4 条真实风险 + 16 条误报上的便宜加固） | 20 |
| 未改（全部是误报） | 21 |
| 审查时额外加固、不计入上面 41 条 | 1（`site.yaml` 里会进 HTML 的 URL） |

4 条真实风险都已修。37 条误报里，16 条顺手做了路径或 slug 约束（不改变现有输入的行为）；没改的 21 条要么会动到 `dist/`，要么落在待合并 AI patch 的上下文里，要么只是测试在加载本仓库自己的文件。

没有新增依赖。`defusedxml` 没加：这台 Python 3.12 的 C 加速版 `XMLParser` 不暴露 `.parser`，`defusedxml` 的常规接法用不上。远程 feed 改用 `xml.parsers.expat`，并拒绝实体声明。标准库 `ElementTree.fromstring` 在这台解释器上会展开内部实体（已用 `&c;` → `bbbb` 验证），不加载外部实体（`&xxe;` 报 undefined entity）。所以真正成立的是 billion laughs 式的拒绝服务，不是读本地文件；两样都关掉了。

## 调用点

| # | 位置（479e309） | 类别 | 真实风险 | 处理 |
|---|---|---|---|---|
| 1 | `scripts/refresh.py:34` | SSRF（`urlopen`） | 是 | 已加固。URL 本身是 `FEEDS` / arXiv 常量，不是用户输入；但默认会跟随重定向，feed 主机可以 302 到别的主机。现在只允许这些常量的 https 主机，重定向也再检查一遍，响应超过 5MB 就拒绝。 |
| 2 | `scripts/refresh.py:39` | XML 实体展开 / XXE | 是 | 已加固。见上文：内部实体会展开。解析改为 expat，`EntityDeclHandler` 直接拒绝实体声明。 |
| 3 | `scripts/refresh.py:76` | 路径穿越（`open` 读队列） | 否 | 已加固。路径是仓库根下的 `review_queue.jsonl`。写入前用 `realpath` + `commonpath` 钉死这个文件。 |
| 4 | `scripts/refresh.py:87` | 路径穿越（`open` 追加队列） | 否 | 已加固。同上。 |
| 5 | `scripts/citations.py:33` | SSRF（`urlopen`） | 是 | 已加固。主机是 Semantic Scholar / OpenAlex 常量；DOI、arXiv id、标题只进 path/query，并且做了 quote，换不了主机。风险同样是重定向。现在白名单只有这两个主机，重定向再检查。 |
| 6 | `scripts/citations.py:65` | SSRF（batch `urlopen`） | 是 | 已加固。同上，走同一个 opener。 |
| 7 | `scripts/citations.py:182` | 路径穿越（读 `citations.json`） | 否 | 已加固。常量 `data/citations.json`。读写都要求 realpath 落在 `data/` 且文件名是 `citations.json`。 |
| 8 | `scripts/citations.py:186` | 路径穿越（读卡片 YAML） | 否 | 未改。`glob(data/systems/*.yaml)`，文件名来自本仓库。 |
| 9 | `scripts/citations.py:189` | 路径穿越（读卡片 YAML） | 否 | 未改。同上。 |
| 10 | `scripts/citations.py:203` | 路径穿越（写 `citations.json`，同一行两次 `open`） | 否 | 已加固。见 #7。 |
| 11 | `build.py:31` | 路径穿越（`taxonomy.yaml`） | 否 | 未改。常量路径。 |
| 12 | `build.py:57` | 路径穿越（`site.yaml`） | 否 | 未改。常量路径。里面的 URL 另见文末补充项。 |
| 13 | `build.py:67` | 路径穿越（newsletter YAML） | 否 | 已加固。`open` 的是 glob 到的文件。slug 来自文件名，另外要求匹配 `[a-z0-9]+(-[a-z0-9]+)*`，避免 `..` 进输出路径。当前没有 newsletter 文件，构建输出不变。 |
| 14 | `build.py:82` | 路径穿越（卡片 YAML） | 否 | 已加固。`open` 本身出不了 `data/systems/`。id 必须等于文件名，并匹配同一 slug 规则。现有 95 个 id 都符合。 |
| 15 | `build.py:304` | 路径穿越（`ui.txt`） | 否 | 未改。常量路径。 |
| 16 | `build.py:328` | 路径穿越（`companies.txt`） | 否 | 未改。常量路径。 |
| 17 | `build.py:407` | 路径穿越（中文 overlay） | 否 | 已通过 #14 的 id 规则覆盖。路径是 `id + ".txt"`，id 不能是 `..` 或带斜杠。文件名本身也不能含 `/`。 |
| 18 | `build.py:457` | 路径穿越（`terms.txt`） | 否 | 未改。常量路径。 |
| 19 | `build.py:835` | 路径穿越（读 `citations.json`） | 否 | 未改。常量路径，只读。 |
| 20 | `build.py:853` | 路径穿越（diagram YAML） | 否 | 已加固。id 使用和卡片相同的 slug 规则。现有 14 个图都符合。 |
| 21 | `build.py:1046` | 路径穿越（topic YAML） | 否 | 未改。slug 在用到输出路径之前已经有同样的正则。 |
| 22 | `build.py:1095` | 路径穿越（中文 topic） | 否 | 未改。slug 来自上一步已校验的值。 |
| 23 | `build.py:1349` | 路径穿越（`write` 写出 HTML） | 否 | 已加固。单个路径分量即使是 `..` 也到不了 `dist/` 外面（前面还有固定目录前缀，文件名又不能含 `/`），最多覆盖 `dist` 里别的页面。`write` 的函数体没改（AI patch 的上下文含这两行），在函数后面套了一层：拒绝绝对路径和 `..` 分量，并用 `commonpath` 把目标钉在 `OUT` 里。`OUT` 仍是 `dist/`，没有改成死锁，以免挡住 AI patch 的 `RECARCH_OUT`。 |
| 24 | `build.py:1358` | DOM XSS（`document.write`） | 否 | 未改。写入的是生成器自己的 404 页，`json.dumps` 并且把 `</` 换成 `<\\/`。没有请求期用户输入。改这里会改变 `dist/`。 |
| 25 | `build.py:1406` | 路径删除（`shutil.rmtree(OUT)`） | 否 | 未改。`OUT` 是仓库下的 `dist/`。这行在 AI patch 的上下文里。 |
| 26 | `build.py:1408` | 路径复制（`copytree` static → dist） | 否 | 未改。两边都是常量。同样在 AI patch 上下文里。 |
| 27 | `scripts/make_assets.py:19` | 路径穿越（读 `ui.txt`） | 否 | 未改。常量路径。 |
| 28 | `scripts/make_assets.py:70` | 路径穿越（写临时 SVG） | 否 | 已加固。临时文件必须落在 `TemporaryDirectory` 里。 |
| 29 | `scripts/make_assets.py:71` | 路径穿越（写临时 HTML） | 否 | 已加固。同上。 |
| 30 | `scripts/make_assets.py:72` | 命令注入（`subprocess` + Chrome） | 否 | 已加固参数路径，不是 shell。参数是列表，没有 `shell=True`。截图路径限制在 `static/`。`--no-sandbox` 留着：这是本地生成已提交的社交图，容器里的 headless Chrome 经常需要它，输入是仓库里的 `ui.txt`。 |
| 31 | `scripts/make_assets.py:76` | 路径穿越（写 `favicon.svg`） | 否 | 已加固。输出必须在 `static/` 下。PNG/ICO 的 `save` 同样检查。 |
| 32 | `scripts/make_assets.py:80` | 路径穿越（写 `og-default.svg`） | 否 | 已加固。同上。 |
| 33 | `tests/carousel_fixture.py:40` | 路径穿越（写测试 HTML） | 否 | 已加固。输出目录是命令行参数（CI 用 `/tmp/car-fixtures`），文件名限制为单个路径段。 |
| 34 | `tests/carousel_fixture.py:44` | 路径穿越（写 `meta.json`） | 否 | 已加固。同上。 |
| 35 | `tests/zh_numbers.test.js:41` | 命令执行（`execFileSync`） | 否 | 未改。`python3 -c` 的脚本是测试文件里的常量，参数是数组，没有 shell。stdin 是测试用例 JSON。 |
| 36 | `tests/carousel.test.js:11` | 代码执行（`eval`） | 否 | 未改。jsdom 执行的是本仓库 `dist/static/carousel.js`。 |
| 37 | `tests/compare.test.js:14` | 代码执行（`runScripts: "dangerously"`） | 否 | 未改。加载的是刚构建的本地页面。 |
| 38 | `tests/compare.test.js:15` | 代码执行（`eval`） | 否 | 未改。同上，本地 `compare.js`。 |
| 39 | `tests/i18n.test.js:105` | 代码执行（`eval`） | 否 | 未改。本地页面和 `app.js`。第 115 行是同一类。 |
| 40 | `tests/lang_toggle.test.js:8` | 代码执行（`runScripts: "dangerously"`） | 否 | 未改。本地页面。第 9 行 `eval` 同一类。 |
| 41 | `tests/notfound.test.js:15` | 代码执行（`runScripts: "dangerously"`） | 否 | 未改。测的是 404 页自己的内联脚本。`tests/sort.test.js:6` 的 `eval` 也是本地 `app.js`，同一类，不单列以免把测试夹具重复计数。 |

补充（不在上面 41 条里）：`build.py` 里 `newsletter.embed_url`、由它推导的 attribution 脚本、`newsletter.public_url`、`feedback.repo` 会进页面。`embed_url` 经 `static/nl.js` 变成 `<script src>`。这些值来自维护者提交的 `site.yaml`，外部攻击者改不了，所以不算外部 SSRF/XSS。仍然加了 https + 主机白名单（`subscribe-forms.beehiiv.com`、`recarch.beehiiv.com`、`github.com`）。当前 `site.yaml` 全部通过，HTML 不变。

## 订阅源

2026-11-02 用仓库里的 User-Agent 实际请求过。没有可用的第一方替换地址，两条都停用，原因写在 `scripts/refresh.py` 的 `DISABLED`，每次运行会打到 stderr，脚本不因此失败。

| 源 | 原 URL | 现在 | 核实 |
|---|---|---|---|
| Uber | `https://www.uber.com/en-US/blog/engineering/rss/` | 停用。没有新 URL | 301 到 `https://www.uber.com/us/en/blog/engineering/rss/`。不带 Accept 或 `Accept: */*` 是 HTTP 406，正文 `Not Acceptable`。`application/rss+xml`、`application/atom+xml`、`application/xml`、`text/xml`、浏览器 Accept，以及浏览器 User-Agent，都是 HTTP 404，不是 feed。`https://www.uber.com/us/en/blog/` 的 HTML 没有 RSS/Atom alternate。`https://eng.uber.com/feed/` 已不存在。第三方根据网页拼的 feed 没有采用。 |
| LinkedIn | `https://engineering.linkedin.com/blog.rss.html` | 停用。没有新 URL | HTTP 404（Feeder 记录自 2024-01 起无响应）。`/blog.rss`、`https://www.linkedin.com/blog/engineering` 以及 `/rss`、`/feed.xml`、`.rss` 都是 404。工程博客 HTML 里 rss/atom 出现次数为 0。 |

其余源在加固后的解析器上复测（条目数 / 标题样本）：

| 源 | 结果 |
|---|---|
| Netflix | 10 条，`Making Failure Diagnosis Reliable with Pensive AI` |
| Pinterest | 10 条 |
| Airbnb | 10 条，`CASTLE: training natural language search...` |
| Spotify | 5 条 |
| Meta Engineering | 9 条 |
| Instacart | 10 条 |
| Etsy | 20 条 |
| arXiv cs.IR | 60 条 |
| DoorDash | HTTP 403。用改前的 `urllib.request.urlopen` 同样 403，URL 和 User-Agent 都没变，不是这次引入的。脚本照旧把失败打到 stderr，不中断。 |

`python3 scripts/refresh.py --days 30` 退出码 0：拉到 134 条，新入队 53 条。队列文件不在仓库里，跑完已删掉，没有进 diff。

## 构建对比

两次都是不设 `SITE_URL` 的 `python3 build.py`（规范地址因此是默认的 `https://recarch.example`），同一天（2026-11-02）。先构建并复制到 `/tmp/recarch-baseline/dist`，改完再构建。

```
diff -r /tmp/recarch-baseline/dist dist
```

退出码 0，diff 输出 0 字节。`diff -rq` 同样无差异。两次都是 84 张在用卡片 × 中英，`dist/` 204 个文件。

## 测试

与 `.github/workflows/pages.yml` 相同，`SITE_URL=https://jdding.github.io/recarch`。测试前用这个变量又构建了一次（这次的 `dist/` 和上面的字节对比不是同一次构建）。

```
npm install --no-save --prefix /tmp/jt jsdom
python3 tests/carousel_fixture.py /tmp/car-fixtures
NODE_PATH=/tmp/jt/node_modules
for t in tests/*.test.js; do node "$t"; done
```

Node v22.23.4。fixture：`python selection tests: ALL PASS`，`pill baseline tests: ALL PASS`。

| 测试 | 结果 |
|---|---|
| carousel.test.js | CAROUSEL: ALL PASS |
| compare.test.js | COMPARE: ALL PASS |
| copy.test.js | 791 checks passed |
| feedback.test.js | 1407 checks passed |
| i18n.test.js | 11860/11860 |
| lang_toggle.test.js | LANG TOGGLE: ALL PASS |
| meta.test.js | 3357 checks passed |
| notfound.test.js | NOT FOUND: ALL PASS |
| retired.test.js | 68/68 |
| sort.test.js | SORT: ALL PASS |
| topics.test.js | 218/218 |
| v2_order.test.js | 1179/1179 |
| zh_numbers.test.js | 23/23 |

全部退出码 0。

## AI patch

`uploads/recarch-ai.patch` 的路径前缀是 `recarch-ai/`，所以：

```
git apply --check -p1 recarch-ai.patch
```

退出码 0。`build.py` 里 patch 碰到的行（import、`OUT`、页脚、卡片页 head、`write()` 函数体、`main()` 里 rmtree / 404 / sitemap 那几处）没有改。路径检查包在 `write()` 后面。

## diff 里没有的东西

`git diff --name-only` 只有 `build.py`、`scripts/citations.py`、`scripts/make_assets.py`、`scripts/refresh.py`、`tests/carousel_fixture.py` 和本文件。没有 PDF，没有 Zotero 导出或全文。`requirements.txt` 未改。
