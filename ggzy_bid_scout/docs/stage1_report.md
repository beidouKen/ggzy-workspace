# Stage1 报告 — 列表页采集能力

## 概述

| 项目 | 内容 |
|------|------|
| 阶段 | Stage1: 列表页采集能力 |
| 目标站点 | https://www.ggzy.gov.cn/deal/dealList.html |
| 测试时间 | 2026-03-17 09:27 |
| 状态 | **已封板 (ACCEPTED)** |

## 采集结果

| 指标 | 结果 | 标准 |
|------|------|------|
| 单页抓取 | 20 条 | >= 10 条 |
| 翻页能力 | 3/3 页 | 可到第 3 页 |
| 总采集条数 | 60 条 | - |
| 总可用记录 | 1,598 条 | - |
| 记录去重 | 0 重复 | 无重复 |
| detail_url 可访问率 | 100% (5/5) | 可打开 |
| 稳定性 | 3/3 次成功 | 连续 3 次 |
| 总耗时 | 12.5s | - |

## API 技术细节

### 端点

```
POST https://www.ggzy.gov.cn/information/pubTradingInfo/getTradList
Content-Type: application/x-www-form-urlencoded
```

### 请求参数

| 参数 | 类型 | 说明 |
|------|------|------|
| FINDTXT | string | 搜索关键词 |
| PAGENUMBER | int | 页码（从 1 开始） |
| DEAL_TIME | string | 时间范围编码（01=今天, 02=近三天, 03=近十天, 04=近一月, 05=近六月） |
| TIMEBEGIN / TIMEEND | date | 日期范围 |
| SOURCE_TYPE | string | 数据源类型（1=省平台） |
| isShowAll | string | 显示全部（1） |

### 响应结构

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "records": [...],
    "total": 1598,
    "size": 20,
    "current": 1,
    "pages": 80
  }
}
```

### 单条记录字段映射

| API 字段 | 输出字段 | 说明 |
|----------|----------|------|
| title | title | 公告标题 |
| publishTime | publish_date | 发布日期 |
| provinceText | region | 省份 |
| transactionSourcesPlatformText | platform | 来源平台 |
| url | detail_url | 详情页链接（需拼接 base URL） |
| businessTypeText | business_type | 业务类型 |
| informationTypeText | info_type | 信息类型 |
| id | record_id | 记录唯一 ID |

## DOM 结构

列表页通过 JS 动态渲染，DOM 结构如下：

```html
<div id="toview">
  <div class="publicont">
    <div>
      <h4>
        <a href="/information/deal/html/a/{province}/{type}/{date}/{id}.html"
           title="公告标题" target="_blank">
          公告标题（关键词高亮用 <span class="p_tit">）
        </a>
        <span class="span_o">2026-03-17</span>
      </h4>
      <p class="p_tw">
        <span>省份：</span><span class="span_on">浙江省</span>
        <span>来源平台：</span><span class="span_on">湖州市公共资源交易网</span>
        <span>业务类型：</span><span class="span_on">政府采购</span>
        <span>信息类型：</span><span class="span_on">采购合同</span>
      </p>
    </div>
  </div>
  <!-- 重复 20 次 -->
</div>
```

## 示例数据

### 记录 1

```json
{
  "title": "德清县体育中心（县少年儿童体育学校）的少体校学生就学、训练、参赛等用车服务采购项目合同",
  "publish_date": "2026-03-17",
  "region": "浙江省",
  "platform": "湖州市公共资源交易网",
  "detail_url": "https://www.ggzy.gov.cn/information/deal/html/a/330000/0203/20260317/003346ed9dd8b0494c7aa507db162810f636.html",
  "business_type": "政府采购",
  "info_type": "采购合同"
}
```

### 记录 2

```json
{
  "title": "上海市竞技体育训练管理中心羽毛球队赞助项目",
  "publish_date": "2026-03-17",
  "region": "上海市",
  "platform": "上海联合产权交易所",
  "detail_url": "https://www.ggzy.gov.cn/information/deal/html/a/310000/9002/20260317/003183a93c49cca84f26af77aa0dd4557c63.html",
  "business_type": "其他",
  "info_type": "成交公示"
}
```

### 记录 3

```json
{
  "title": "九鼎赣饶国际项目管理有限公司关于新余市体育事业产业发展中心采购新余市体育中心体育场扩音系统及视频监控采购(项目编号:JDGR2026-XY-J002)的竞争性谈判公告",
  "publish_date": "2026-03-17",
  "region": "江西省",
  "platform": "江西省公共资源交易信息网",
  "detail_url": "https://www.ggzy.gov.cn/information/deal/html/a/360000/0201/20260317/0036a3c66d96193d42bc80f07279a8de7a95.html",
  "business_type": "政府采购",
  "info_type": "采购/资审公告"
}
```

## 潜在风险

| 风险 | 等级 | 说明 |
|------|------|------|
| 反爬机制 | 中 | 目前 HTTP 直连可用，但高频访问可能触发限流 |
| SSL/网络波动 | 低 | 已实现 3 次重试 + 指数退避 |
| API 变更 | 低 | API 端点稳定，但参数格式可能变更 |
| 编码问题 | 低 | API 返回 UTF-8 JSON，已处理 |
| platform 字段缺失 | 低 | 部分记录 platform 为 null，已做空值兼容 |

## 文件清单

| 文件 | 用途 |
|------|------|
| `tools/ggzy_list_fetch.py` | 列表页采集工具 |
| `skills/ggzy_query_navigator.md` | OpenClaw Skill 文档 |
| `tests/test_stage1_list_fetch.py` | 自检脚本 |
| `data/raw/stage1_test_result.json` | 测试数据 |
| `data/raw/stage1_test_log.txt` | 测试日志 |
| `data/raw/api_sample.json` | API 响应样本 |
| `docs/stage1_report.md` | 本报告 |

## 结论

Stage1 列表页采集能力全部测试通过（5 PASS / 0 FAIL），满足封板标准。可进入 Stage2。
