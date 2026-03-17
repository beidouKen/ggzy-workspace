# Stage2 报告 — 详情页抽取能力

## 概述

| 项目 | 内容 |
|------|------|
| 阶段 | Stage2: 详情页抽取能力 |
| 目标 | 从单条公告详情页提取结构化字段 |
| 测试时间 | 2026-03-17 09:36 |
| 状态 | **已封板 (ACCEPTED)** |

## 测试结果

### 封板标准检验（10 条随机公告）

| 字段 | 要求 | 实际 | 结果 |
|------|------|------|------|
| 标题 (title) | 100% | 100% (10/10) | PASS |
| 正文 (content_text) | ≥90% | 100% (10/10) | PASS |
| 附件 (attachments) | ≥80% | 100% (6/6 检出) | PASS |

### 补充字段提取率

| 字段 | 提取率 | 说明 |
|------|--------|------|
| publish_date | 100% | 所有页面均有 |
| issuer | 50% | 部分类型（成交公示、更正事项）无此字段 |
| agency | 60% | 部分类型无代理机构信息 |
| budget | 10% | 多数公告类型不含预算金额 |

## 页面结构分析

### 双层页面架构

详情页采用 A/B 两层结构：

```
A-page: /information/deal/html/a/{province}/{type}/{date}/{id}.html
  ├── h4.h4_o → 标题
  ├── p.p_o → 项目编号 / 信息来源
  ├── ul.ul_toggle → 多标签导航（公告、中标、合同、更正）
  └── JS: firstLastUrl → B-page 默认 URL

B-page: /information/deal/html/b/{province}/{type}/{date}/{id}.html
  ├── h4.h4_o → 标题
  ├── p.p_o → 发布时间 / 信息来源
  └── div#mycontent → 正文内容
      ├── table.detail_Table (合同类: th/td 键值对)
      └── 纯文本/HTML (公告类: 招标内容)
```

### 内容类型分布

| 信息类型 | 编码 | 特点 |
|----------|------|------|
| 招标/资审公告 (0201) | 长文本，含附件 | issuer/budget 通常可提取 |
| 中标公告 (0202) | 中等文本 | 含中标人信息 |
| 采购合同 (0203) | 表格格式 | structured_fields 丰富 |
| 更正事项 (0204) | 短文本 | 字段较少 |
| 中标候选人 (0104) | 结果公示 | 格式多样 |
| 成交公示 (9002) | 极短文本 | 字段最少 |

## 提取字段说明

| 输出字段 | 来源 | 提取方式 |
|----------|------|----------|
| title | A-page h4.h4_o | CSS 选择器 |
| publish_date | B-page p.p_o | 正则 (发布时间/签署时间) |
| region | 列表页 provinceText | 继承自 Stage1 |
| issuer | B-page 正文 / table | 正则 (多模式匹配) |
| agency | B-page 正文 / table | 正则 (多模式匹配) |
| budget | B-page 正文 / table | 正则 (多模式匹配) |
| content_text | B-page #mycontent | 全文提取 |
| attachments | B-page a[href] | URL 后缀匹配 |
| project_code | A-page p.p_o | 正则 |
| source_platform | A/B-page label#platformName | CSS 选择器 |

## 示例数据

### 招标公告类

```json
{
  "title": "九鼎赣饶国际项目管理有限公司关于...竞争性谈判公告",
  "publish_date": "2026-03-17 00:00",
  "issuer": "新余市体育事业产业发展中心",
  "agency": "九鼎赣饶国际项目管理有限公司",
  "budget": "1980000.00 元",
  "project_code": "JDGR2026-XY-J002",
  "source_platform": "新余市公共资源交易中心",
  "content_text_length": 1679
}
```

### 合同类

```json
{
  "title": "德清县体育中心...用车服务采购项目合同",
  "publish_date": "2026-03-17 00:32",
  "issuer": "德清县体育中心（德清县少年儿童体育学校）",
  "budget": "0元 人民币",
  "structured_fields": {
    "采购人名称": "德清县体育中心（德清县少年儿童体育学校）",
    "中标（成交）供应商名称": "湖州新国旅外事旅游汽车服务有限公司",
    "合同金额": "0元 人民币",
    "合同签署时间": "2026-03-17 00:32:09"
  }
}
```

## 潜在风险

| 风险 | 等级 | 说明 |
|------|------|------|
| issuer/budget 低提取率 | 中 | 不同省份/类型的页面格式差异大 |
| B-page URL 变更 | 低 | 依赖 JS 变量 firstLastUrl |
| 内容编码 | 低 | 统一 UTF-8 处理 |
| 原文链接指向外部 | 低 | 部分公告含省级平台原文链接 |

## 文件清单

| 文件 | 用途 |
|------|------|
| `tools/ggzy_detail_fetch.py` | 详情页抽取工具 |
| `skills/ggzy_detail_extractor.md` | OpenClaw Skill 文档 |
| `tests/test_stage2_detail_fetch.py` | 自检脚本 |
| `data/raw/stage2_test_result.json` | 测试数据 |
| `docs/stage2_report.md` | 本报告 |

## 结论

Stage2 详情页抽取能力全部通过封板标准（title=100%, content=100%, attachments=100%）。可进入 Stage3。
