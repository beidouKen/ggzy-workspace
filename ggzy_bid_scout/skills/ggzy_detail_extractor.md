# Skill: ggzy_detail_extractor

## 用途

解析全国公共资源交易平台（ggzy.gov.cn）单条公告的详情页，提取结构化字段。

## 触发条件

当用户需要：
- 查看某条招标/采购公告的详细信息
- 提取公告正文、预算、采购人等关键字段
- 获取公告附件列表

## 输入参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| detail_url | string | 是 | 详情页 URL（A-page URL，来自列表页） |

## 输出结构

```json
{
  "title": "公告标题",
  "publish_date": "2026-03-17 00:00",
  "region": "江西省",
  "issuer": "新余市体育事业产业发展中心",
  "agency": "九鼎赣饶国际项目管理有限公司",
  "budget": "1980000.00 元",
  "content_text": "正文文本（纯文本）",
  "attachments": [
    {"name": "招标公告.pdf", "url": "https://..."}
  ],
  "project_code": "JDGR2026-XY-J002",
  "source_platform": "新余市公共资源交易中心",
  "original_link": "https://www.jxsggzy.cn/...",
  "structured_fields": {
    "采购人名称": "新余市体育事业产业发展中心",
    "合同金额": "1980000.00 元"
  }
}
```

## 调用方式

### 命令行

```bash
python tools/ggzy_detail_fetch.py "https://www.ggzy.gov.cn/information/deal/html/a/360000/0201/20260317/xxx.html"

# JSON 输出
python tools/ggzy_detail_fetch.py --json "URL"

# 保存到文件
python tools/ggzy_detail_fetch.py --output data/raw/detail.json "URL"
```

### Python API

```python
from tools.ggzy_detail_fetch import fetch_detail

result = fetch_detail("https://www.ggzy.gov.cn/information/deal/html/a/...")
print(result.title, result.budget, result.issuer)
```

## 页面结构

详情页采用 A/B 两层结构：

- **A-page** (`/html/a/`): 容器页面，包含标题、项目编号、多标签导航
- **B-page** (`/html/b/`): 实际内容页，包含正文、表格、附件

工具自动从 A-page 获取 B-page URL 并提取内容。

## 支持的内容格式

1. **表格格式**（采购合同类）: `table.detail_Table` 中的 th/td 键值对
2. **文本格式**（招标公告类）: `div#mycontent` 中的纯文本/HTML

## 注意事项

1. 该 Skill 只处理单条公告，批量采集使用 ggzy_batch_collector
2. 正文文本不传入 LLM 上下文，直接落盘 JSON
3. 附件仅提取 URL 不下载文件
