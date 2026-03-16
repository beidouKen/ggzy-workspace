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

- **关键词**：用户指定（如：医疗、足球、教育、建筑等）
- **省份**：可选覆盖，默认"广东"
- **翻页数**：可选，默认全部页

## ⚠️ 关键约束

1. **此网站不支持 URL 查询参数**——所有筛选条件必须通过页面 DOM 交互设置。禁止在 URL 上拼接 `keyword`、`province`、`timeRange` 等参数，拼了也不会生效。
2. 全局规则禁止 `browser act kind:fill` 和 `browser act kind:type`。**必须用 `browser evaluate` 执行 JavaScript 来注入文本和操作下拉框**。
3. 每次导航或 AJAX 请求后，aria ref 编号会失效。**每次交互前必须重新 `browser snapshot`** 获取最新 ref。
4. 筛选链接（近十天、交易公告等）是 `<a href="javascript:;">`，点击后会触发 AJAX 异步加载，**点击后必须 sleep 2-3 秒** 等待数据刷新。

## 操作流程

### Step 1：打开网站（不带任何参数）

```
browser navigate url:"https://www.ggzy.gov.cn/deal/dealList.html"
```

等待 3 秒让页面完全加载：

```
browser act kind:wait duration:3000
```

### Step 2：用 evaluate 一次性设置全部筛选条件 + 关键词 + 触发搜索

用一个 `browser evaluate` 调用完成所有设置并触发搜索。将 `<关键词>` 替换为用户指定的关键词，将 `<省份>` 替换为目标省份（默认"广东"）：

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
    nativeInputValueSetter.call(input, '<关键词>');
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

### Step 3：验证筛选条件是否生效（最多重试 2 次）

先截图做视觉确认：

```
browser screenshot
```

再用 evaluate 程序化验证当前筛选状态（将 `<省份>` 替换为目标省份）：

```javascript
browser evaluate expression:"(function() {
  var result = {};

  // 检查时间范围：找到 class 含 active/selected/on 的时间链接
  var timeLinks = document.querySelectorAll('.search_tiaojian a');
  for (var i = 0; i < timeLinks.length; i++) {
    var cl = timeLinks[i].className || '';
    var parent = timeLinks[i].parentElement ? timeLinks[i].parentElement.className : '';
    if (cl.indexOf('active') >= 0 || cl.indexOf('selected') >= 0 || cl.indexOf('on') >= 0
        || parent.indexOf('active') >= 0 || parent.indexOf('selected') >= 0 || parent.indexOf('on') >= 0) {
      result.timeRange = timeLinks[i].textContent.trim();
    }
  }

  // 检查省份
  var selects = document.querySelectorAll('select');
  for (var j = 0; j < selects.length; j++) {
    if (selects[j].selectedIndex > 0) {
      result.province = selects[j].options[selects[j].selectedIndex].text;
      break;
    }
  }
  if (!result.province) result.province = '不限';

  // 检查信息类型
  var infoLinks = document.querySelectorAll('.search_tiaojian a');
  for (var k = 0; k < infoLinks.length; k++) {
    var t = infoLinks[k].textContent.trim();
    if ((t === '交易公告' || t === '成交公示' || t === '不限') &&
        (infoLinks[k].className.indexOf('active') >= 0 ||
         (infoLinks[k].parentElement && infoLinks[k].parentElement.className.indexOf('active') >= 0))) {
      result.infoType = t;
    }
  }

  // 检查关键词输入框
  var input = document.querySelector('input[placeholder*=\"关键字\"]');
  result.keyword = input ? input.value : '';

  return JSON.stringify(result);
})()"
```

**验证规则**：
- `timeRange` 应为"近十天"
- `province` 应为目标省份（如"广东"）
- `infoType` 应为"交易公告"
- `keyword` 应为用户指定的关键词

**如果任何条件不一致**，重新执行 Step 2，最多重试 **2 次**。3 次仍不一致则截图告知用户筛选条件可能存在问题，继续用当前状态搜索。

### Step 4：抓取第 1 页数据

```
browser snapshot refs:"aria"
```

从 snapshot 中提取：
- 搜索记录总数（形如"搜索记录数:XXX"）
- 每条公告的：标题、日期、省份、来源平台、业务类型、信息类型、详情链接
- 分页信息（形如"页码X/Y"）
- 翻页按钮的 ref 编号

截图保存：

```
browser screenshot
```

### Step 4.5：空结果检测与主体词识别

从 Step 4 的 snapshot 中读取"搜索记录数"。**如果搜索记录数为 0**，执行以下流程：

#### 1) 判断是否为多词关键词

如果用户输入的关键词是单个词（如"医疗"），直接告知用户无结果并结束。

如果是多词组合（如"新冠医疗"、"足球场地建设"、"污水处理设备"），进入主体词识别。

#### 2) AI 识别主体词

对关键词进行语义分析，判断哪个是**主体词**（用户真正关心的核心名词），哪个是**修饰词**（限定范围的附加描述）。

识别原则：
- 主体词是用户搜索意图的核心对象
- 修饰词是对核心对象的补充说明或领域限定
- 示例：
  - "新冠医疗" → 主体词"新冠"（用户关心的是新冠相关项目），修饰词"医疗"
  - "足球场地建设" → 主体词"足球"，修饰词"场地建设"
  - "污水处理设备" → 主体词"污水处理"，修饰词"设备"
  - "校园安防监控" → 主体词"安防监控"，修饰词"校园"

**只给出一个最可能的主体词**，不做多选。

#### 3) 与用户确认

向用户发送确认消息，格式如下：

> 搜索「<原始关键词>」在<省份>近十天的交易公告中无结果（记录数为 0）。
>
> 分析认为核心主体词是「<主体词>」，是否用「<主体词>」重新搜索？
> 你也可以告诉我一个其他关键词。

**必须等待用户回复，禁止自动执行重搜。**

#### 4) 用户确认后重新搜索

根据用户回复：
- 用户同意 → 用主体词替换 `<关键词>`，从 **Step 1** 重新执行完整搜索流程
- 用户给出新关键词 → 用新关键词替换 `<关键词>`，从 **Step 1** 重新执行

#### 5) 重搜仍无结果

如果重搜后搜索记录数仍为 0，**再次询问用户**：

> 搜索「<当前关键词>」仍然没有结果。是否要换一个关键词继续搜索？或者结束本次查询？

- 用户给出新关键词 → 继续重搜
- 用户选择结束 → 告知用户无结果，结束任务

### Step 5：翻页抓取

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
  // 备选：点击「下一页」
  for (var j = 0; j < pageLinks.length; j++) {
    if (pageLinks[j].textContent.indexOf('下一页') >= 0 || pageLinks[j].title === '下一页') {
      pageLinks[j].click();
      return 'ok: clicked next page';
    }
  }
  return 'error: page link not found';
})()"
```

等待 3 秒 → `browser screenshot` → `browser snapshot` 抓取数据。

重复直到达到用户指定的页数或没有更多页。

### Step 6：生成 HTML 报告

将所有收集到的公告信息整理成 HTML 文档，包含：
- 搜索条件摘要（关键词、省份、时间范围、信息类型）
- 总记录数和总页数
- 表格形式展示每条公告：序号、标题（可点击链接）、日期、省份、业务类型、信息类型
- 每页截图的缩略图

## 输出

- 搜索结果的 HTML 报告文件路径
- 每页截图的媒体路径列表

## 故障排除

| 现象 | 原因 | 处理 |
|------|------|------|
| 搜索结果显示全国数据，未按省份过滤 | evaluate 中省份选择未生效 | 重新 snapshot 确认 select 元素，检查 option text 是否精确匹配 |
| 点击"近十天"后结果未变化 | AJAX 未完成就截图了 | 增加等待时间到 5 秒 |
| ref 点击超时 | 页面交互后旧 ref 失效 | 重新 snapshot 获取最新 ref |
| 搜索按钮找不到 | DOM 结构可能有变化 | 用 snapshot 检查按钮实际标签和 class |
| 翻页无反应 | 页码链接定位不准 | 先 snapshot 找到分页区域的准确 ref，用 click ref |
| 搜索记录数为 0 | 关键词组合过于具体或该领域近期无公告 | 进入 Step 4.5 主体词识别流程，与用户确认后用主体词重搜 |
| 筛选条件验证失败（Step 3 不一致） | evaluate 设置未生效，DOM 结构可能变化 | 重试 Step 2（最多 2 次），仍失败则截图告知用户 |

## 示例调用

### 示例 1：正常搜索（有结果）

用户请求："帮我搜索广东近十天关于医疗设备的招标公告"

执行步骤：
1. `browser navigate` 打开基础 URL（不带参数）
2. `browser evaluate` 一次性设置：近十天 + 广东 + 交易公告 + 关键词"医疗设备" + 点击搜索
3. 等待 3 秒 → `browser screenshot` + evaluate 验证筛选条件
4. `browser snapshot` 抓取第 1 页数据 + 截图
5. `browser evaluate` 翻到第 2 页 → 等待 → snapshot + 截图
6. 汇总所有结果生成 HTML 报告

### 示例 2：无结果 → 主体词识别 → 用户确认重搜

用户请求："帮我搜索广东近十天关于新冠医疗的招标公告"

执行步骤：
1. `browser navigate` 打开基础 URL
2. `browser evaluate` 设置筛选条件 + 关键词"新冠医疗" + 搜索
3. 验证筛选条件
4. `browser snapshot` → 发现搜索记录数为 0
5. AI 分析"新冠医疗"，识别主体词为"新冠"
6. 向用户确认：「搜索'新冠医疗'无结果，核心主体词为'新冠'，是否用'新冠'重新搜索？」
7. 用户回复"好的" → 用"新冠"从 Step 1 重新执行
8. 搜索到结果 → 正常抓取 + 生成报告
