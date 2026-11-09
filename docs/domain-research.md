# RecArch 自有域名调研

调研日期 2026-11-02（Asia/Shanghai）。只做了查询，没有注册任何账号，没有购买任何域名。

## 1. 候选域名

可用性来自各 TLD 官方注册局的 RDAP 接口，经 rdap.org 跳转，返回 404 表示尚未注册；同时用 Google DNS 查 NS 记录，全部是 NXDOMAIN。RDAP 只能说明现在没人注册，不排除该域名在注册商处是溢价词，所以最终以 Cloudflare 搜索框和结账页显示为准。

价格单位美元每年。Cloudflare 一列取自 cfdomainpricing.com 对 Cloudflare 官方价目表的镜像，页面标注更新于 2026-11-01，因为 Cloudflare 官方价目页靠脚本渲染，抓取不到数字。Cloudflare 按成本价出售，首年和续费通常相同，页面上能看到例外，例如 .dev 首年 8.20 续费 12.20。Porkbun 一列取自 Porkbun 官方价目页，首年带 1st Yr Sale 标记的是促销价。

| 域名 | 现在是否可注册 | Cloudflare 首年 | Cloudflare 续费 | Porkbun 首年 | Porkbun 续费 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| recarch.dev | 可，RDAP 404 | 8.20 | 12.20 | 8.75 | 12.87 | 推荐。强制 HTTPS，与技术站定位相符，三年总价最低档 |
| recarch.org | 可，RDAP 404 | 8.50 | 11.20 | 7.98 | 11.84 | 续费最便宜，像开放项目；英文里 org 常被理解为非营利 |
| recarch.app | 可，RDAP 404 | 8.20 | 14.20 | 8.75 | 14.93 | 强制 HTTPS，续费较高 |
| recarch.com | 可，RDAP 404 | 10.46 | 10.46 | 11.81 | 11.81 | 最通用。注意 Verisign 自 2026-11-01 起上调批发价，第三方数据对 Cloudflare 新价有出入，pikkly.dev 写 10.46，domainoffer.net 写 11.17，下单前看结账页 |
| recarch.ai | 可，RDAP 404 | 80.00 | 80.00 | 82.70 | 82.70 | 贵，每年约八倍，仅当品牌需要 AI 字样时才值得 |

没有列入 .io 和 .co：这两个后缀没有可用的 RDAP 接口，我这里 43 端口的 whois 也不通，只能确认 DNS 没有记录，不能确认可注册。价格上 .io 在 Cloudflare 首年 32.00 续费 50.00，不划算。

来源：
- Cloudflare 价格镜像 https://cfdomainpricing.com/
- Cloudflare 价格参考 https://pikkly.dev/domains/registrar/cloudflare/ 和 https://domainoffer.net/tld/dev/cloudflare
- Cloudflare 官方介绍 https://www.cloudflare.com/products/registrar/ 和 https://developers.cloudflare.com/registrar/
- Porkbun 官方价目 https://porkbun.com/products/domains
- Porkbun 价格交叉验证 https://mystackplan.com/providers/porkbun 和 https://domainoffer.net/tld/dev/porkbun

建议买 recarch.dev，Cloudflare 一家完成注册和 DNS，每年约 12 美元。

## 2. Cloudflare Registrar 必须同时用 Cloudflare DNS

在 Cloudflare Registrar 买的域名只能使用 Cloudflare 的名称服务器，不能改成别家的 DNS，想用别家 DNS 只能把域名转出。所以买下来之后 DNS 记录就在 Cloudflare 面板里管理，下面两项都在那里配置。
来源：https://developers.cloudflare.com/registrar/faq/ 、https://developers.cloudflare.com/registrar/get-started/register-domain/ 、https://www.cloudflare.com/registrar-terms/

## 3. GitHub Pages 绑定自有域名，同时用 mcp 子域名放 Worker

网页继续放在 GitHub Pages，MCP 服务放在 Cloudflare Worker，两者用不同主机名，互不影响。

1. 在仓库 Settings 的 Pages 里填 Custom domain，例如 recarch.dev，保存。当前部署用的是 GitHub Actions 工作流，这时不会生成 CNAME 文件，也不需要。建议先在账号设置里做域名验证，防止被别人接管。
2. 到 Cloudflare 的 DNS 记录里加四条 A 记录指向 185.199.108.153、185.199.109.153、185.199.110.153、185.199.111.153，可再加对应的四条 AAAA 记录 2606:50c0:8000::153 到 2606:50c0:8003::153。再加一条 www 的 CNAME 指向 jdding.github.io，注意只写用户名域名，不带仓库名。
3. 这几条记录先设成仅 DNS，不走橙色云代理，先让 GitHub 签发证书，再在 Pages 设置里勾选 Enforce HTTPS，最长要等 24 小时。
4. 不要用泛域名记录，GitHub 文档警告有接管风险。
5. Worker 的域名单独加：mcp-worker/wrangler.toml 里已经注释好 routes，取消注释并写入 pattern = "mcp.recarch.dev"、custom_domain = true，执行 deploy 后 Cloudflare 会自动建 DNS 记录和证书。要求该主机名上没有已有的 CNAME 记录，并且域名所在 zone 已经在 Cloudflare 激活。
6. 站点现在的地址是 jdding.github.io/recarch/，带路径前缀。换成自有域名后站点在根路径，构建时把 SITE_URL 设为 https://recarch.dev 重新构建，canonical、sitemap、llms.txt 里的链接才会一起变。旧的 jdding.github.io/recarch/ 地址 GitHub 会自动跳转到新域名。
7. MCP 地址占位符 https://mcp.recarch.example/mcp 用环境变量 RECARCH_MCP_URL=https://mcp.recarch.dev/mcp 在构建时替换，页面上的“尚未启用”提示也随之消失。

来源：
- https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site
- https://developers.cloudflare.com/workers/configuration/routing/custom-domains/

## 4. workers.dev 在中国大陆不可靠，所以必须绑自有域名

GreatFire 的监测显示 workers.dev 下能得出结论的 210 个地址在大陆全部被封，手段是 DNS 污染、丢包和连接重置，最近一次测试在 2026-11-01。Cloudflare 官方社区的回复也说 workers.dev 在中国被列入黑名单，解决办法是用自己的域名。所以 wrangler.toml 里 workers_dev 只是开发用，对外的 MCP 地址一律用 mcp.<自有域名>。

要注意：绑自有域名只是明显改善，不保证稳定。Cloudflare 普通套餐在大陆的访问质量看运营商线路，没有承诺。另外在境外注册商（Cloudflare、Porkbun 等）买的域名通常无法做 ICP 备案，要在大陆正式运营需要先转入境内注册商，这是后话。

Cloudflare Web Analytics 的脚本也从 Cloudflare 域名加载，在大陆可能加载失败，只影响统计数据，不影响页面渲染。

来源：
- https://en.greatfire.org/domain/workers.dev
- https://community.cloudflare.com/t/cloudflare-workers-suspected-of-being-blocked-in-china/382155
- https://chendahuang.com/playbook/cloudflare/chapters/06-china-access
- https://developers.cloudflare.com/china-network/llms-full.txt
