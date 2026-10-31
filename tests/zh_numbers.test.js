// The Chinese number check converts English magnitude words by value and still rejects every new number.
const { execFileSync } = require("child_process");
const path = require("path");
const root = path.join(__dirname, "..");
const py = `
import json, build
cases = json.loads(open(0).read())
out = []
for en, zh in cases:
    extra, probs = build.zh_number_problems(zh, en)
    out.append([sorted(extra), probs])
print(json.dumps(out))
`;
const good = [
  ["more than 1 billion active users", "超过十亿活跃用户"],
  ["over 1 million apps", "超过一百万个应用"],
  ["more than half a billion users", "超过五亿用户"],
  ["hundreds of billions of edges", "数千亿条边"],
  ["20 million users", "两千万用户"],
  ["7.7 million items", "770 万个 item"],
  ["1.5 trillion parameters", "1.5 万亿个参数"],
  ["a hundred billion nodes", "千亿节点"],
  ["a billion-scale item pool", "十亿级的 item 池"],
  ["several million candidates", "数百万个候选"],
  ["0.14 billion users", "1.4 亿用户"],
  ["54,000 items", "5.4 万个 item"],
  ["up to 100K events", "最多十万个事件"],
  ["2.5% lift over 5 days", "提升 2.5%，持续 5 天"],
];
const bad = [
  ["1 billion users", "超过二十亿用户", "20 亿 is not 1 billion"],
  ["1 million apps", "一千万个应用", "10 million is not 1 million"],
  ["half a billion users", "十亿用户", "wrong magnitude"],
  ["billions of users", "数千亿用户", "billions is 数十亿"],
  ["1 billion users", "超过 1 billion 用户", "English magnitude word left"],
  ["half a billion users", "超过 half a billion 用户", "English magnitude word left"],
  ["20 million users", "21 个用户", "new digit number"],
  ["20 million users", "两千万用户，增长 3%", "new digit number beside a good magnitude"],
  ["20 million users", "2000 万用户", "2000 万 is 20 million: allowed, so see good case"],
];
const run = (cases) => JSON.parse(execFileSync("python3", ["-c", py], { cwd: root, input: JSON.stringify(cases.map((c) => c.slice(0, 2))) }).toString());
let fail = 0, n = 0;
const g = run(good);
good.forEach((c, i) => { n++; if (g[i][0].length || g[i][1].length) { fail++; console.log("FAIL should pass:", c[0], "|", c[1], JSON.stringify(g[i])); } });
const b = run(bad);
bad.forEach((c, i) => {
  n++; const rejected = b[i][0].length || b[i][1].length;
  const expectPass = c[2].includes("allowed");
  if (!!rejected === expectPass) { fail++; console.log("FAIL expected", expectPass ? "pass" : "reject", ":", c[0], "|", c[1], JSON.stringify(b[i])); }
});
console.log(`zh_numbers.test.js: ${n - fail}/${n} checks passed`);
process.exit(fail ? 1 : 0);
