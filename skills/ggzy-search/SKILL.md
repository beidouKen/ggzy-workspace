---
name: ggzy-search
description: 全国公共资源交易平台(ggzy)公告搜索与报告生成工具。当用户提到招标、投标、中标、开标、招标公告、中标公告、中标结果、招投标、招标信息、采购公告、政府采购、公共资源交易、交易公告、工程招标、货物招标、服务招标、竞争性谈判、竞争性磋商、询价公告、单一来源、资格预审、建设工程、土地使用权、矿业权、国有产权，或需要在全国公共资源交易平台上搜索、查询、抓取任何交易公告信息时使用此技能。支持自定义关键词搜索，自动翻页抓取全部结果并生成 HTML 报告。默认筛选广东省近十天的交易公告。
metadata: { "openclaw": { "emoji": "🔍" } }
---

# ggzy-search Skill

全国公共资源交易平台公告搜索与报告生成技能。

## 用途

搜索全国公共资源交易平台（https://www.ggzy.gov.cn/deal/dealList.html）上的交易公告，支持自定义关键词，自动翻页抓取全部结果，并生成 HTML 报告。

## 默认筛选条件

- **发布时间**：近十天
- **省份**：广东
- **信息类型**：交易公告

## 可变参数

- **关键词**：一个或多个，用户指定。支持两种输入方式：
  - 自然语言："帮我搜索医疗和足球的招标公告"
  - 列举式："搜索以下关键词：医疗、足球、教育"
- **省份**：可选覆盖，默认"广东"
- **翻页数**：可选，默认全部页（对每个关键词生效）

## ⚠️ 关键约束

1. **此网站不支持 URL 查询参数**——所有筛选条件必须通过页面 DOM 交互设置。禁止在 URL 上拼接 `keyword`、`province`、`timeRange` 等参数，拼了也不会生效。
2. 全局规则禁止 `browser act kind:fill` 和 `browser act kind:type`。**必须用 `browser evaluate` 执行 JavaScript 来注入文本和操作下拉框**。
3. 每次导航或 AJAX 请求后，aria ref 编号会失效。**每次交互前必须重新 `browser snapshot`** 获取最新 ref。
4. 筛选链接（近十天、交易公告等）是 `<a href="javascript:;">`，点击后会触发 AJAX 异步加载，**点击后必须 sleep 2-3 秒** 等待数据刷新。
5. **多关键词必须逐个搜索**——此网站搜索框只支持单关键词，不能一次搜多个。每个关键词需要独立执行一轮完整的搜索流程（导航 → 设置筛选 → 搜索 → 翻页抓取）。

## 操作流程

### Step 1：解析关键词列表

从用户输入中提取关键词，构建一个**关键词列表**。

解析规则：
- 自然语言中的"和""与""以及"是分隔符："医疗和足球" → `["医疗", "足球"]`
- 中文顿号、逗号是分隔符："医疗、足球、教育" → `["医疗", "足球", "教育"]`
- 单个关键词："医疗设备" → `["医疗设备"]`
- 注意区分**多关键词**和**多词组合关键词**：
  - "医疗和足球" = 两个独立关键词 → `["医疗", "足球"]`
  - "医疗设备" = 一个组合关键词 → `["医疗设备"]`
  - "新冠医疗和足球场地" = 两个组合关键词 → `["新冠医疗", "足球场地"]`

初始化结果收集器：
- `results = {}`（关键词 → 搜索结果数组的映射）
- `emptyKeywords = []`（搜索记录数为 0 的关键词列表）

### Step 2：打开网站（不带任何参数）

```
browser navigate url:"https://www.ggzy.gov.cn/deal/dealList.html"
```

等待 3 秒让页面完全加载：

```
browser act kind:wait duration:3000
```

---

### 🔁 Step 3 ~ Step 6：对每个关键词循环执行

**对关键词列表中的每个关键词 `<当前关键词>`**，依次执行以下步骤：

### Step 3：设置筛选条件 + 当前关键词 + 触发搜索

用一个 `browser evaluate` 调用完成所有设置并触发搜索。将 `<当前关键词>` 替换为当前循环的关键词，将 `<省份>` 替换为目标省份（默认"广东"）：

```javascript
browser evaluate expression:"(function() {
  // 1) 点击「近十天」
  var links = document.querySelectorAll('.search_tiaojian a');
  for (var i = 0; i < links.length; i++) {
    if (links[i].textContent.trim() === '近十天') {
      links[i].click();
      break;
    }
  }

  // 2) 选择省份
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

  // 3) 点击「交易公告」
  for (var m = 0; m < links.length; m++) {
    if (links[m].textContent.trim() === '交易公告') {
      links[m].click();
      break;
    }
  }

  // 4) 输入关键词
  var input = document.querySelector('input[placeholder*=\"关键字\"]');
  if (!input) input = document.querySelector('.search_key input');
  if (input) {
    var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    nativeInputValueSetter.call(input, '<当前关键词>');
    input.dispatchEvent(new Event('input', {bubbles: true}));
    input.dispatchEvent(new Event('change', {bubbles: true}));
  }

  // 5) 点击搜索按钮
  var btns = document.querySelectorAll('button, input[type=button], a');
  for (var n = 0; n < btns.length; n++) {
    if (btns[n].textContent.trim() === '搜索') {
      btns[n].click();
      return 'ok: filters set, search triggered';
    }
  }
  // 备选：直接调用 onclick
  var searchBtn = document.querySelector('.search_btn') || document.querySelector('[onclick*=search]');
  if (searchBtn) { searchBtn.click(); return 'ok: fallback search clicked'; }
  return 'error: search button not found';
})()"
```

执行后等待 3 秒让搜索结果加载：

```
browser act kind:wait duration:3000
```

### Step 4：验证筛选条件是否生效（最多重试 2 次）

先截图做视觉确认：

```
browser screenshot
```

再用 evaluate 程序化验证当前筛选状态：

```javascript
browser evaluate expression:"(function() {
  var result = {};

  var timeLinks = document.querySelectorAll('.search_tiaojian a');
  for (var i = 0; i < timeLinks.length; i++) {
    var cl = timeLinks[i].className || '';
    var parent = timeLinks[i].parentElement ? timeLinks[i].parentElement.className : '';
    if (cl.indexOf('active') >= 0 || cl.indexOf('selected') >= 0 || cl.indexOf('on') >= 0
        || parent.indexOf('active') >= 0 || parent.indexOf('selected') >= 0 || parent.indexOf('on') >= 0) {
      result.timeRange = timeLinks[i].textContent.trim();
    }
  }

  var selects = document.querySelectorAll('select');
  for (var j = 0; j < selects.length; j++) {
    if (selects[j].selectedIndex > 0) {
      result.province = selects[j].options[selects[j].selectedIndex].text;
      break;
    }
  }
  if (!result.province) result.province = '不限';

  var infoLinks = document.querySelectorAll('.search_tiaojian a');
  for (var k = 0; k < infoLinks.length; k++) {
    var t = infoLinks[k].textContent.trim();
    if ((t === '交易公告' || t === '成交公示' || t === '不限') &&
        (infoLinks[k].className.indexOf('active') >= 0 ||
         (infoLinks[k].parentElement && infoLinks[k].parentElement.className.indexOf('active') >= 0))) {
      result.infoType = t;
    }
  }

  var input = document.querySelector('input[placeholder*=\"关键字\"]');
  result.keyword = input ? input.value : '';

  return JSON.stringify(result);
})()"
```

**验证规则**：
- `timeRange` 应为"近十天"
- `province` 应为目标省份（如"广东"）
- `infoType` 应为"交易公告"
- `keyword` 应为当前关键词

**如果任何条件不一致**，重新执行 Step 3，最多重试 **2 次**。3 次仍不一致则截图告知用户，继续用当前状态搜索。

### Step 5：抓取数据 + 检查结果数

```
browser snapshot refs:"aria"
```

从 snapshot 中提取：
- 搜索记录总数（形如"搜索记录数:XXX"）
- 每条公告的：标题、日期、省份、来源平台、业务类型、信息类型、详情链接
- 分页信息（形如"页码X/Y"）

截图保存：

```
browser screenshot
```

**如果搜索记录数为 0**：将当前关键词加入 `emptyKeywords` 列表，**跳过 Step 6，直接进入下一个关键词**。

**如果搜索记录数 > 0**：将提取的数据存入 `results[<当前关键词>]`，继续 Step 6。

### Step 6：翻页抓取

对每一页执行以下循环：

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

等待 3 秒 → `browser screenshot` → `browser snapshot` 抓取数据，追加到 `results[<当前关键词>]`。

重复直到达到用户指定的页数或没有更多页。

### 🔁 切换到下一个关键词

当前关键词的搜索完成后，如果还有下一个关键词，**重新导航到基础 URL**：

```
browser navigate url:"https://www.ggzy.gov.cn/deal/dealList.html"
browser act kind:wait duration:3000
```

然后回到 **Step 3** 用下一个关键词继续。

---

### Step 7：空结果批量处理

所有关键词搜索完成后，检查 `emptyKeywords` 列表。**如果为空**（所有关键词都有结果），跳过此步直接到 Step 8。

**如果 `emptyKeywords` 不为空**，执行以下流程：

#### 1) 对每个无结果的关键词识别主体词

对 `emptyKeywords` 中的每个关键词进行语义分析：
- 如果是单个词（如"医疗"），标记为"单词，无法拆分"
- 如果是多词组合（如"新冠医疗"），识别出主体词

识别原则：
- 主体词是用户搜索意图的核心对象
- 修饰词是对核心对象的补充说明或领域限定
- 示例：
  - "新冠医疗" → 主体词"新冠"
  - "足球场地建设" → 主体词"足球"
  - "污水处理设备" → 主体词"污水处理"
  - "校园安防监控" → 主体词"安防监控"

#### 2) 一次性向用户汇报并确认

向用户发送一条汇总消息，格式如下：

> 以下关键词在<省份>近十天的交易公告中无结果：
>
> 1. 「新冠医疗」— 建议用主体词「新冠」重新搜索
> 2. 「足球场地」— 建议用主体词「足球」重新搜索
> 3. 「量子计算」— 单个词，无法进一步拆分
>
> 请告诉我：
> - 哪些需要用建议的主体词重新搜索？
> - 哪些需要换一个关键词？
> - 哪些直接跳过？

**必须等待用户回复，禁止自动执行。**

#### 3) 根据用户回复补搜

对用户确认需要重搜的关键词，逐个执行 Step 2 ~ Step 6 的完整流程。补搜后仍无结果的关键词，**再次询问用户**是否要换词继续或放弃。

### Step 8：生成 HTML 报告（按关键词分组）

将所有收集到的数据整理成**一份** HTML 文档，结构如下：

1. **报告头部**
   - 搜索条件摘要：省份、时间范围、信息类型
   - 关键词列表及各自的搜索记录数
   - 总记录数（所有关键词之和）

2. **按关键词分组的结果**（每个关键词一个独立章节）
   - 章节标题：关键词名称 + 记录数
   - 表格：序号、标题（可点击链接）、日期、省份、业务类型、信息类型
   - 该关键词对应的截图缩略图

3. **无结果关键词汇总**（如有）
   - 列出搜索过但无结果的关键词

## 输出

- 搜索结果的 HTML 报告文件路径（一份报告包含所有关键词的结果）
- 每页截图的媒体路径列表

## 故障排除

| 现象 | 原因 | 处理 |
|------|------|------|
| 搜索结果显示全国数据，未按省份过滤 | evaluate 中省份选择未生效 | 重新 snapshot 确认 select 元素，检查 option text 是否精确匹配 |
| 点击"近十天"后结果未变化 | AJAX 未完成就截图了 | 增加等待时间到 5 秒 |
| ref 点击超时 | 页面交互后旧 ref 失效 | 重新 snapshot 获取最新 ref |
| 搜索按钮找不到 | DOM 结构可能有变化 | 用 snapshot 检查按钮实际标签和 class |
| 翻页无反应 | 页码链接定位不准 | 先 snapshot 找到分页区域的准确 ref，用 click ref |
| 搜索记录数为 0（单关键词） | 关键词组合过于具体或该领域近期无公告 | 进入 Step 7 主体词识别流程，与用户确认后重搜 |
| 搜索记录数为 0（多关键词中部分为空） | 部分关键词无匹配 | 先跑完全部关键词，在 Step 7 批量汇报无结果的词 |
| 筛选条件验证失败（Step 4 不一致） | evaluate 设置未生效，DOM 结构可能变化 | 重试 Step 3（最多 2 次），仍失败则截图告知用户 |
| 多关键词搜索时页面状态残留 | 上一个关键词的筛选状态未清除 | 每个关键词搜索前重新 navigate 到基础 URL |

## 示例调用

### 示例 1：单关键词搜索（有结果）

用户请求："帮我搜索广东近十天关于医疗设备的招标公告"

执行步骤：
1. 解析关键词列表：`["医疗设备"]`
2. `browser navigate` 打开基础 URL
3. `browser evaluate` 设置：近十天 + 广东 + 交易公告 + 关键词"医疗设备" + 搜索
4. 验证筛选条件
5. 抓取数据 + 翻页
6. 生成 HTML 报告

### 示例 2：多关键词搜索（全部有结果）

用户请求："帮我搜索广东近十天关于医疗和足球的招标公告"

执行步骤：
1. 解析关键词列表：`["医疗", "足球"]`
2. `browser navigate` 打开基础 URL
3. 搜索"医疗" → 验证 → 抓取数据 + 翻页
4. 重新 `browser navigate` 到基础 URL
5. 搜索"足球" → 验证 → 抓取数据 + 翻页
6. 生成一份 HTML 报告，按"医疗"和"足球"分组展示

### 示例 3：多关键词搜索（部分无结果）

用户请求："搜索以下关键词的广东招标公告：医疗、新冠疫苗、足球"

执行步骤：
1. 解析关键词列表：`["医疗", "新冠疫苗", "足球"]`
2. 搜索"医疗" → 有结果 → 抓取
3. 搜索"新冠疫苗" → 搜索记录数为 0 → 加入 emptyKeywords
4. 搜索"足球" → 有结果 → 抓取
5. 批量汇报：「以下关键词无结果：'新冠疫苗'——建议用主体词'新冠'重搜。是否重搜？」
6. 用户确认 → 用"新冠"补搜
7. 生成报告：医疗（XX条）、新冠（XX条）、足球（XX条）

### 示例 4：单关键词无结果 → 主体词识别

用户请求："帮我搜索广东近十天关于新冠医疗的招标公告"

执行步骤：
1. 解析关键词列表：`["新冠医疗"]`
2. 搜索"新冠医疗" → 记录数为 0
3. 汇报：「'新冠医疗'无结果，核心主体词为'新冠'，是否用'新冠'重新搜索？」
4. 用户确认 → 用"新冠"重搜
5. 有结果 → 正常抓取 + 生成报告
