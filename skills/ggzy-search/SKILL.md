---
name: ggzy-search
description: 全国公共资源交易平台(ggzy)公告搜索与报告生成工具。当用户提到招标、投标、中标、开标、招标公告、中标公告、中标结果、招投标、招标信息、采购公告、政府采购、公共资源交易、交易公告、工程招标、货物招标、服务招标、竞争性谈判、竞争性磋商、询价公告、单一来源、资格预审、建设工程、土地使用权、矿业权、国有产权，或需要在全国公共资源交易平台上搜索、查询、抓取任何交易公告信息时使用此技能。支持自定义关键词搜索，自动翻页抓取全部结果并生成 HTML 报告。默认筛选广东省近十天的交易公告。
metadata: { "openclaw": { "emoji": "🔍" } }
---

# ggzy-search Skill

搜索全国公共资源交易平台（https://www.ggzy.gov.cn/deal/dealList.html）上的交易公告，支持单个或多个关键词，自动翻页抓取并生成按关键词分组的 HTML 报告。

## 🚨 执行纪律（最高优先级，必须遵守）

1. **禁止中途暂停询问用户**。一旦开始搜索循环，必须按顺序跑完所有关键词，中途不得停下来问用户"要不要继续""要不要换方案"。
2. **禁止尝试 Skill 未定义的替代方案**。不允许尝试 URL 参数、API 调用、web_fetch 或任何本文档未列出的方法。只用本文档定义的 `browser evaluate` 方式。
3. **禁止自行优化或跳步**。即使认为某步骤"可能不需要"，也必须完整执行。每个关键词都走完 Step 3→4→5→6 全流程。
4. **必须输出进度日志**。每完成一个关键词，立即输出一行进度（不需要等用户回复），格式：`[N/总数] 关键词: XX条 ✓` 或 `[N/总数] 关键词: 0条（无结果）✓`
5. **空结果只记录不处理**。循环中遇到 0 条结果，记入 emptyKeywords 后立即进入下一个关键词。主体词分析和用户确认放在全部跑完之后。
6. **必须生成 HTML 报告**。Step 8 不可跳过，无论有多少关键词都必须生成一份报告文件。

## 参数与约束

**默认筛选**：近十天 / 广东 / 交易公告

**可变参数**：
- 关键词（必填，一个或多个）：自然语言"医疗和足球" → `["医疗","足球"]`；列举式"医疗、足球" → `["医疗","足球"]`
- 省份（可选，默认"广东"）
- 翻页数（可选，默认全部页）

**技术约束**：
- 网站不支持 URL 查询参数，所有筛选条件必须通过 `browser evaluate` 操作 DOM
- 禁止 `browser act kind:fill` 和 `browser act kind:type`，必须用 evaluate 注入文本
- 每次导航/AJAX 后 aria ref 失效，交互前必须重新 snapshot
- 筛选链接点击后触发 AJAX，必须 sleep 2-3 秒等待加载
- 多关键词必须逐个搜索，每个关键词需要独立执行完整流程

---

## 操作流程

### Step 1：解析关键词列表

从用户输入提取关键词数组。"和""与""以及"、顿号、逗号为分隔符。区分多关键词（"医疗和足球"→2 个）和组合关键词（"医疗设备"→1 个）。

初始化：`results = {}`, `emptyKeywords = []`

### Step 2：打开网站

```
browser navigate url:"https://www.ggzy.gov.cn/deal/dealList.html"
browser act kind:wait duration:3000
```

---

### 🔁 Step 3~6：对每个关键词循环执行

### Step 3：设置筛选 + 关键词 + 搜索

将 `<当前关键词>` 和 `<省份>` 替换后执行：

```javascript
browser evaluate expression:"(function() {
  function isActive(el) {
    var cl = el.className || '';
    var pcl = el.parentElement ? el.parentElement.className : '';
    return cl.indexOf('active') >= 0 || cl.indexOf('selected') >= 0 || cl.indexOf('on') >= 0
        || pcl.indexOf('active') >= 0 || pcl.indexOf('selected') >= 0 || pcl.indexOf('on') >= 0;
  }

  var links = document.querySelectorAll('.search_tiaojian a');
  for (var i = 0; i < links.length; i++) {
    if (links[i].textContent.trim() === '近十天') {
      if (!isActive(links[i])) links[i].click();
      break;
    }
  }

  var selects = document.querySelectorAll('select');
  for (var j = 0; j < selects.length; j++) {
    var opts = selects[j].options;
    for (var k = 0; k < opts.length; k++) {
      if (opts[k].text === '<省份>') {
        selects[j].value = opts[k].value;
        selects[j].dispatchEvent(new Event('change', {bubbles: true}));
        break;
      }
    }
  }

  for (var m = 0; m < links.length; m++) {
    if (links[m].textContent.trim() === '交易公告') {
      if (!isActive(links[m])) links[m].click();
      break;
    }
  }

  var input = document.querySelector('input[placeholder*=\"关键字\"]');
  if (!input) input = document.querySelector('.search_key input');
  if (input) {
    var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    nativeInputValueSetter.call(input, '');
    input.dispatchEvent(new Event('input', {bubbles: true}));
    nativeInputValueSetter.call(input, '<当前关键词>');
    input.dispatchEvent(new Event('input', {bubbles: true}));
    input.dispatchEvent(new Event('change', {bubbles: true}));
  }

  var btns = document.querySelectorAll('button, input[type=button], a');
  for (var n = 0; n < btns.length; n++) {
    if (btns[n].textContent.trim() === '搜索') {
      btns[n].click();
      return 'ok: filters set, search triggered';
    }
  }
  var searchBtn = document.querySelector('.search_btn') || document.querySelector('[onclick*=search]');
  if (searchBtn) { searchBtn.click(); return 'ok: fallback search clicked'; }
  return 'error: search button not found';
})()"
```

等待 3 秒：`browser act kind:wait duration:3000`

### Step 4：验证筛选条件（不一致则重试 Step 3，最多 2 次）

`browser screenshot` 截图，然后执行验证脚本：

```javascript
browser evaluate expression:"(function() {
  var r = {};
  var links = document.querySelectorAll('.search_tiaojian a');
  for (var i = 0; i < links.length; i++) {
    var cl = (links[i].className || '') + ' ' + (links[i].parentElement ? links[i].parentElement.className : '');
    if (cl.indexOf('active') >= 0 || cl.indexOf('selected') >= 0 || cl.indexOf('on') >= 0)
      r.timeRange = links[i].textContent.trim();
  }
  var selects = document.querySelectorAll('select');
  for (var j = 0; j < selects.length; j++) {
    if (selects[j].selectedIndex > 0) { r.province = selects[j].options[selects[j].selectedIndex].text; break; }
  }
  if (!r.province) r.province = '不限';
  for (var k = 0; k < links.length; k++) {
    var t = links[k].textContent.trim();
    var kcl = (links[k].className || '') + ' ' + (links[k].parentElement ? links[k].parentElement.className : '');
    if ((t === '交易公告' || t === '成交公示') && (kcl.indexOf('active') >= 0 || kcl.indexOf('selected') >= 0))
      r.infoType = t;
  }
  var input = document.querySelector('input[placeholder*=\"关键字\"]');
  r.keyword = input ? input.value : '';
  return JSON.stringify(r);
})()"
```

验证：`timeRange`=近十天, `province`=目标省份, `infoType`=交易公告, `keyword`=当前关键词。不一致则重试 Step 3，最多 2 次。3 次仍失败则继续执行。

### Step 5：抓取数据

`browser snapshot refs:"aria"` 提取搜索记录总数、每条公告详情、分页信息。`browser screenshot` 截图。

- 记录数为 0 → 加入 `emptyKeywords`，**跳过 Step 6，直接进入下一个关键词**
- 记录数 > 0 → 存入 `results[<当前关键词>]`，继续 Step 6

### Step 6：翻页抓取

```javascript
browser evaluate expression:"(function() {
  var pageLinks = document.querySelectorAll('.pagination a, .page a, [class*=page] a');
  for (var i = 0; i < pageLinks.length; i++) {
    if (pageLinks[i].textContent.trim() === '<目标页码>') {
      pageLinks[i].click();
      return 'ok: clicked page <目标页码>';
    }
  }
  for (var j = 0; j < pageLinks.length; j++) {
    if (pageLinks[j].textContent.indexOf('下一页') >= 0 || pageLinks[j].title === '下一页') {
      pageLinks[j].click();
      return 'ok: clicked next page';
    }
  }
  return 'error: page link not found';
})()"
```

等待 3 秒 → screenshot → snapshot 抓取数据。重复直到达到用户指定页数或无更多页。

### 🔁 切换关键词（强制重置页面）

**禁止**直接 navigate 到相同 URL。必须强制硬刷新：

```javascript
browser evaluate expression:"location.href = 'https://www.ggzy.gov.cn/deal/dealList.html?_t=' + Date.now();"
```

等待 **5 秒**：`browser act kind:wait duration:5000`

验证页面已重置：

```javascript
browser evaluate expression:"(function() {
  var input = document.querySelector('input[placeholder*=\"关键字\"]');
  var keyword = input ? input.value : '';
  var selects = document.querySelectorAll('select');
  var province = '不限';
  for (var j = 0; j < selects.length; j++) {
    if (selects[j].selectedIndex > 0) { province = selects[j].options[selects[j].selectedIndex].text; break; }
  }
  return JSON.stringify({ inputEmpty: keyword === '', province: province, pageReady: !!document.querySelector('.search_tiaojian') });
})()"
```

如果 `inputEmpty` 为 `false`，强制清空：

```javascript
browser evaluate expression:"(function() {
  var input = document.querySelector('input[placeholder*=\"关键字\"]');
  if (input) { var s = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set; s.call(input,''); input.dispatchEvent(new Event('input',{bubbles:true})); }
  var selects = document.querySelectorAll('select');
  for (var j = 0; j < selects.length; j++) { selects[j].selectedIndex = 0; selects[j].dispatchEvent(new Event('change',{bubbles:true})); }
  return 'ok: forced reset';
})()"
```

等待 2 秒后回到 Step 3。

**输出进度日志**：`[N/总数] 关键词: XX条 ✓`

---

### Step 7：空结果批量处理

所有关键词跑完后，如果 `emptyKeywords` 为空则直接到 Step 8。

如果有无结果的关键词，一次性向用户汇报：
- 多词组合：识别主体词（核心名词），建议重搜。如"新冠医疗"→主体词"新冠"
- 单个词：标记"无法拆分"

汇报格式：

> 以下关键词无结果：
> 1. 「新冠医疗」— 建议用「新冠」重搜
> 2. 「足球」— 单个词，无法拆分
>
> 哪些需要重搜？哪些跳过？

等待用户回复后，对需要重搜的关键词执行 Step 2~6。补搜仍无结果则再次询问用户。

### Step 8：生成 HTML 报告（不可跳过）

文件名：`ggzy_report_<YYYYMMDD>_<HHmmss>.html`

用 `exec` 或 `write_file` 写入以下模板（用实际数据替换 `{{占位符}}`，`{{#循环}}...{{/循环}}` 对每项重复）：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>公共资源交易公告搜索报告</title>
<style>
  body { font-family: -apple-system, "Microsoft YaHei", sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; color: #333; }
  h1 { color: #1a56db; border-bottom: 2px solid #1a56db; padding-bottom: 10px; }
  h2 { color: #1e40af; margin-top: 40px; border-left: 4px solid #1e40af; padding-left: 12px; }
  .summary { background: #f0f7ff; border-radius: 8px; padding: 16px 20px; margin: 16px 0; }
  .summary p { margin: 4px 0; }
  .keyword-tag { display: inline-block; background: #dbeafe; color: #1e40af; padding: 2px 10px; border-radius: 12px; margin: 2px 4px; font-size: 14px; }
  .empty-tag { background: #fee2e2; color: #991b1b; }
  table { width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 14px; }
  th { background: #1e40af; color: #fff; padding: 10px 8px; text-align: left; }
  td { padding: 8px; border-bottom: 1px solid #e5e7eb; }
  tr:hover td { background: #f9fafb; }
  a { color: #1a56db; text-decoration: none; }
  a:hover { text-decoration: underline; }
  .screenshot { max-width: 100%; border: 1px solid #e5e7eb; border-radius: 4px; margin: 8px 0; }
  .footer { margin-top: 40px; padding-top: 16px; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 12px; }
  .no-result { background: #fef2f2; border-radius: 8px; padding: 12px 16px; color: #991b1b; }
</style>
</head>
<body>
<h1>公共资源交易公告搜索报告</h1>
<div class="summary">
  <p><strong>生成时间：</strong>{{生成时间}}</p>
  <p><strong>搜索条件：</strong>省份={{省份}}，发布时间=近十天，信息类型=交易公告</p>
  <p><strong>关键词：</strong>{{#每个关键词}}<span class="keyword-tag">{{关键词}} ({{记录数}}条)</span>{{/每个关键词}}</p>
  <p><strong>总记录数：</strong>{{总记录数}} 条</p>
</div>
{{#每个有结果的关键词}}
<h2>「{{关键词}}」— {{记录数}} 条结果</h2>
<table>
  <thead><tr><th>序号</th><th>标题</th><th>日期</th><th>省份</th><th>业务类型</th><th>信息类型</th></tr></thead>
  <tbody>
    {{#每条公告}}<tr><td>{{序号}}</td><td><a href="{{链接}}" target="_blank">{{标题}}</a></td><td>{{日期}}</td><td>{{省份}}</td><td>{{业务类型}}</td><td>{{信息类型}}</td></tr>{{/每条公告}}
  </tbody>
</table>
{{#如果有截图}}{{#每张截图}}<img class="screenshot" src="{{截图路径}}" alt="第{{页码}}页截图">{{/每张截图}}{{/如果有截图}}
{{/每个有结果的关键词}}
{{#如果有无结果的关键词}}
<h2>无结果的关键词</h2>
<div class="no-result"><ul>{{#每个无结果关键词}}<li><span class="keyword-tag empty-tag">{{关键词}}</span></li>{{/每个无结果关键词}}</ul></div>
{{/如果有无结果的关键词}}
<div class="footer">
  <p>数据来源：<a href="https://www.ggzy.gov.cn" target="_blank">全国公共资源交易平台</a> | 由 OpenClaw ggzy-search Skill 自动生成</p>
</div>
</body>
</html>
```

写入后向用户报告文件路径和每页截图路径。

## 故障排除

| 现象 | 处理 |
|------|------|
| 筛选条件未生效 | 重试 Step 3（最多 2 次） |
| 后续关键词条件没选上 | isActive() 防 toggle + 先清空再填入 + 硬刷新 |
| 页面状态残留 | 切换时用 `location.href + Date.now()` 硬刷新 |
| 搜索记录数 0 | 记入 emptyKeywords，全部跑完后 Step 7 批量处理 |
| 翻页无反应 | snapshot 获取最新 ref 后 click |

## 示例

用户："搜索以下关键词的广东招标公告：医疗、新冠疫苗、足球"

```
Step 1: 解析 → ["医疗", "新冠疫苗", "足球"]
Step 2: navigate 打开网站
Step 3~6: 搜索"医疗" → 验证 → 抓取 → 翻页
  [1/3] 医疗: 45条 ✓
🔁 硬刷新 → 重置验证
Step 3~6: 搜索"新冠疫苗" → 验证 → 0条 → 跳过翻页
  [2/3] 新冠疫苗: 0条（无结果）✓
🔁 硬刷新 → 重置验证
Step 3~6: 搜索"足球" → 验证 → 抓取 → 翻页
  [3/3] 足球: 8条 ✓
Step 7: 汇报「新冠疫苗」无结果，建议用「新冠」重搜 → 用户确认 → 补搜
Step 8: 生成 ggzy_report_20260316_210000.html
```
