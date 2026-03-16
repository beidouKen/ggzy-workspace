---
name: price-compare
description: 电商多平台智能调研工具。当用户需要比较商品价格、查看评价、对比优惠券、预售信息、外卖价格，或任何涉及多个电商/生活服务平台的搜索、对比、分析任务时使用此技能。支持京东、淘宝、天猫、拼多多、抖音商城、美团、饿了么等平台。
metadata: { "openclaw": { "emoji": "🛒" } }
---

# 电商多平台智能调研

## 能力范围

不仅限于价格对比，还包括：
- **价格对比**：同一商品在多个平台的售价
- **好评/差评分析**：各平台用户评价对比
- **优惠信息**：优惠券、满减、会员价、预售价
- **预售/发售时间**：新品上市时间对比
- **外卖/生活服务**：美团、饿了么等外卖平台价格对比
- **商品规格对比**：同类商品不同品牌/型号的参数对比
- **任何用户提出的多平台调研需求**

## 核心原则（必须严格遵守）

⛔ **禁止事项（违反会导致任务失败）**：
1. **禁止使用 `sessions_spawn`** — 不要创建子 agent / 后台任务，所有操作在当前会话中直接执行
2. **禁止使用 `message` 工具** — webchat 下该工具会报错，直接在回复文本中输出内容
3. **禁止使用 `browser act kind:fill`** — 容易参数出错导致整个任务失败。如果需要在搜索框输入，改用 `browser navigate` 拼接 URL 参数的方式
4. **禁止放弃** — 单个平台失败绝不终止任务，跳过继续下一个

✅ **必须事项**：
- **宿主机浏览器**：通过 Chrome 扩展控制用户的 Chrome，有登录态和 cookie
- **image 工具是你的眼睛**：所有页面内容通过 `image` 工具读取，主模型不能直接看图
- **每个平台保存截图**：截图路径从 `MEDIA:` 行提取，最终生成 HTML 报告时嵌入
- **健壮容错**：浏览器报错时重试一次，再失败降级到 `web_search`
- **所有操作在当前会话中同步执行**，逐个平台串行完成

## 平台搜索 URL

| 平台 | 搜索URL | 备注 |
|------|---------|------|
| 京东 | `https://search.jd.com/Search?keyword={关键词}&enc=utf-8` | |
| 淘宝 | `https://s.taobao.com/search?q={关键词}` | |
| 天猫 | `https://list.tmall.com/search_product.htm?q={关键词}` | 与淘宝共用账号 |
| 拼多多 | `https://mobile.yangkeduo.com/search_result.html?search_key={关键词}` | 移动版，PC 可能异常 |
| 抖音商城 | `https://www.douyin.com/search/{关键词}?type=general` | |
| 美团外卖 | `https://waimai.meituan.com/` | 需手动搜索 |
| 饿了么 | `https://www.ele.me/` | 需手动搜索 |

用户指定了平台就只查指定的；未指定则默认查 **京东、淘宝、天猫**（最稳定的三个）。用户要求更多再加。

## 操作流程

### 1. 理解需求

分析用户想要什么：
- **比什么**：价格？评价？优惠？规格？
- **比哪些**：哪些商品、哪些平台
- **关键词策略**：如果第一次搜不到，自动尝试变体关键词（加空格、换同义词、加品牌全称等）

如果用户需求模糊，简短确认后开始。

### 2. 逐个平台采集

对每个平台执行以下流程：

**步骤 A：导航**

调用 browser 工具时，**必须使用正确的参数格式**：

```
browser navigate url:"{搜索URL}"
```

等待页面加载（必须用 exec，不要用 browser 的 sleep）：
```
exec command:"sleep 5"
```

**步骤 B：截图 + 识别**

截图时只需：
```
browser screenshot
```

**⚠️ browser 工具正确用法（只用这几个，别用其他的）**：

1. **打开页面**（最常用，搜索商品把关键词拼在 URL 里）：
   ```
   browser navigate url:"https://search.jd.com/Search?keyword={用户的关键词}&enc=utf-8"
   ```

2. **截图**（返回 MEDIA: 路径，记录文件名用于报告和图像识别）：
   ```
   browser screenshot
   ```
   截图返回类似 `MEDIA:/home/node/.openclaw/media/browser/abc123.png`。
   - 提取**文件名**（如 `abc123.png`）
   - 用 `image` 工具验证截图内容是否正确（是搜索结果还是登录页等）
   - 记录文件名，生成 HTML 报告时用相对路径 `../media/browser/{文件名}`

3. **向下滚动**（查看更多商品）：
   ```
   browser scroll direction:down amount:800
   ```

4. **获取页面元素树**（仅在需要点击某个按钮时使用）：
   ```
   browser snapshot
   ```

5. **点击元素**（ref 必须来自上面 snapshot 的结果）：
   ```
   browser click ref:"12"
   ```

**⛔ 绝对不要用的 browser 命令**：
- ~~`browser act kind:fill`~~ — 报 "fields are required" 错误
- ~~`browser type`~~ — 报 "request required" 错误
- ~~`browser open`~~ — 会打开新标签页导致 tab not found
- 任何未在上面 5 个之外的 browser 命令

**注意**：`browser navigate` 会在已 attach 的标签页中导航（不会开新标签页），这是正确的行为。

## ⚠️ browser 工具报错时的自救规则（必须遵守）

**当 browser 工具返回错误时，不要立即放弃或切换到 web_search！按以下步骤排查：**

1. **"fields are required" 或 "request required"**
   → 说明你用了错误的 browser 命令。**立即改用正确的命令重试**：
   - 不要用 `browser act kind:fill`，改用 `browser navigate url:"..."` 把关键词拼在 URL 里
   - 不要用 `browser type`，同上
   - 重试时只用上面列出的 5 个命令

2. **"tab not found"**
   → 标签页丢失。**等 3 秒后重试 `browser navigate`**：
   ```
   exec command:"sleep 3"
   browser navigate url:"{搜索URL}"
   ```
   如果连续 2 次 tab not found，告诉用户检查扩展后等待回复。

3. **"no tab is connected"**
   → 扩展未 attach。告诉用户点击扩展图标，等回复后重试。

4. **"timed out"**
   → 网络慢。等待后重试：
   ```
   exec command:"sleep 5"
   browser navigate url:"{搜索URL}"
   ```

**核心规则：每种错误至少重试 2 次，才能降级到 web_search。不要一次报错就放弃浏览器。**

记录截图路径（从返回的 `MEDIA:` 提取），后面生成报告要用。

```
image prompt:"请仔细阅读这张页面截图，回答：
1. 页面类型：搜索结果 / 登录页 / 访问频繁 / 验证码 / 无结果 / 其他
2. 如果是搜索结果：列出所有可见商品的【名称】【价格（原价+促销价）】【店铺】【销量/评价数（如可见）】
3. 如果搜索无结果或结果不相关：说明情况
4. 如果是登录页/验证码/错误页：描述页面内容" image:{截图路径}
```

**步骤 C：根据结果分支处理**

#### ✅ 搜索结果 → 记录数据，可选滚动查看更多

记录 image 工具返回的商品信息。如需更多数据：
```
browser scroll direction:down amount:800
exec command:"sleep 2"
browser screenshot
```
再用 `image` 工具读取，然后**继续下一个平台**。

#### 🔍 无结果 / 结果不相关 → 换关键词重试

尝试最多 2 个变体关键词（加空格分词、换同义词、补全品牌名等），每个变体重新导航+截图。全部无结果则记录"该平台未找到相关商品"，**继续下一个平台**。

#### 🔐 登录页 → 告诉用户去浏览器登录

输出：
> 🔐 **{平台名}需要登录**
> 请在你的浏览器中完成登录，完成后回复"**好了**"，或回复"**跳过**"。

**停止，等用户回复。** 回复后重新导航到搜索页。

#### 🧩 验证码/滑块 → 让用户处理

输出：
> 🧩 **{平台名}出现验证码**，请在浏览器中完成验证，完成后回复"**好了**"。

**停止，等用户回复。**

#### ⚠️ 访问频繁 → 等待重试

```
exec command:"sleep 10"
```
重新导航，最多重试 2 次。仍然失败则**降级到 web_search**：

```
web_search query:"{关键词} {平台名} 价格" search_lang:"zh-hans"
```

记录来源为"网络搜索（非实时）"。

#### ❌ 浏览器报错（tab not found 等）→ 重试 + 降级

如果浏览器工具返回错误（如 `tab not found`、`timed out`）：

1. **第一次**：告诉用户检查浏览器扩展
   > ⚠️ 浏览器连接异常，请确认 Chrome 中 OpenClaw 扩展图标显示为 **ON**。确认后回复"**好了**"。
   
   等用户回复后重试。

2. **第二次仍失败**：降级到 `web_search`
   ```
   web_search query:"{关键词} {平台名} 价格" search_lang:"zh-hans"
   ```
   记录来源为"网络搜索（浏览器不可用）"。

**绝不因单个平台失败而终止整个任务。**

### 3. 生成 HTML 报告

所有平台采集完成后，使用 `exec` 工具生成一个 HTML 文件：

```
exec command:"cat > /home/node/.openclaw/workspace/report.html << 'HTMLEOF'
{HTML内容}
HTMLEOF"
```

HTML 报告模板（根据实际数据填充）：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{调研主题} - 多平台调研报告</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
  h1 { color: #333; border-bottom: 3px solid #ff4500; padding-bottom: 10px; }
  h2 { color: #555; margin-top: 30px; }
  .summary { background: #fff; border-radius: 8px; padding: 20px; margin: 15px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
  .best-price { background: linear-gradient(135deg, #ff4500, #ff6b35); color: #fff; border-radius: 8px; padding: 20px; margin: 15px 0; }
  .best-price h3 { margin-top: 0; }
  table { width: 100%; border-collapse: collapse; margin: 15px 0; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
  th { background: #ff4500; color: #fff; padding: 12px; text-align: left; }
  td { padding: 12px; border-bottom: 1px solid #eee; }
  tr:hover { background: #fff5f0; }
  .price { font-weight: bold; color: #ff4500; font-size: 1.1em; }
  .platform-section { margin: 20px 0; }
  .screenshot { max-width: 100%; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.15); margin: 10px 0; }
  .tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.85em; margin: 2px; }
  .tag-lowest { background: #e8f5e9; color: #2e7d32; }
  .tag-warning { background: #fff3e0; color: #e65100; }
  .tag-error { background: #fce4ec; color: #c62828; }
  .footer { margin-top: 30px; padding: 15px; text-align: center; color: #999; font-size: 0.9em; }
</style>
</head>
<body>
<h1>🛒 {调研主题}</h1>
<p>查询时间：{当前时间} | 关键词：{关键词列表}</p>

<div class="best-price">
  <h3>💡 最优选择</h3>
  <p>{推荐内容，如最低价平台和理由}</p>
</div>

<h2>📊 对比总览</h2>
<table>
  <tr><th>#</th><th>平台</th><th>商品名称</th><th>价格</th><th>店铺</th><th>数据来源</th><th>备注</th></tr>
  <!-- 逐行填入各平台数据 -->
  <tr><td>1</td><td>京东</td><td>xxx</td><td class="price">¥xxx</td><td>xxx</td><td>浏览器实时</td><td>-</td></tr>
</table>

<h2>📸 各平台截图</h2>
<!-- 每个平台一个截图区块，用相对路径引用截图文件 -->
<div class="platform-section">
  <h3>京东</h3>
  <img class="screenshot" src="../media/browser/{京东截图文件名}.png" alt="京东搜索结果">
</div>

<div class="platform-section">
  <h3>淘宝</h3>
  <img class="screenshot" src="../media/browser/{淘宝截图文件名}.png" alt="淘宝搜索结果">
</div>

<!-- 更多平台同理，src 统一用 ../media/browser/{文件名} -->

<h2>⚠️ 未成功查询的平台</h2>
<ul>
  <li>{平台名}: {原因}</li>
</ul>

<div class="footer">
  由 OpenClaw 智能调研工具生成 | 数据仅供参考，以各平台实际页面为准
</div>
</body>
</html>
```

生成后输出：

> 📄 **调研报告已生成**：`/home/node/.openclaw/workspace/report.html`
> 你可以用浏览器打开查看完整的图文报告。

然后在回复文本中也输出一份**精简的 Markdown 版本**（表格 + 建议），方便在聊天窗口直接阅读。

## 容错策略总结

| 情况 | 第一步 | 第二步 | 第三步 |
|------|--------|--------|--------|
| 搜索无结果 | 换关键词重试（最多2次） | 降级 web_search | 记录"未找到" |
| 登录页 | 告诉用户去浏览器登录，等回复 | 用户跳过则记录 | - |
| 验证码/滑块 | 让用户在浏览器处理，等回复 | 用户跳过则记录 | - |
| 访问频繁 | sleep 10 后重试 | 再试一次 | 降级 web_search |
| 浏览器报错 | 提示用户检查扩展，等回复后重试 | 降级 web_search | 记录来源 |
| 单个平台彻底失败 | **绝不终止任务**，跳过继续下一个 | 最终报告中标注 | - |

## 注意事项

- **每个平台最多 3~4 次浏览器操作**（navigate + screenshot + 可选 scroll + 可选换关键词）
- **两个平台之间间隔 3 秒**（`sleep 3`），避免短时间大量请求
- **淘宝和天猫共用账号**，登录淘宝后天猫也能用
- **cookie 持久化**：宿主机浏览器登录一次后续免登录
- **用户能看到浏览器**：遇到登录/验证码直接文字告知，不需要截图展示
- **截图流程**：`browser screenshot` → 提取文件名 → `image` 工具验证内容 → 记录文件名用于报告
- **web_search 是最后手段**：浏览器多次失败后才用，`search_lang` 参数中文必须用 `"zh-CN"`（不是 `zh-hans`）
- **关键词灵活变换**：搜不到时主动调整关键词（加空格、换同义词、加品牌全称等）
- **HTML 报告中截图路径**：使用相对路径 `../media/browser/{文件名}`，报告生成在 workspace 目录，截图在 media/browser 目录，相对路径可直接在宿主机浏览器打开显示
- **多商品任务**：如果用户要比较多个商品，逐个商品分别走完所有平台，最后合并到一个报告
