# Skill: ggzy_query_navigator

## 用途

查询全国公共资源交易平台（ggzy.gov.cn）交易公告列表，返回当前页结构化数据。

## 触发条件

当用户需要：
- 搜索招标/采购/交易公告
- 按关键词查询公共资源交易信息
- 获取特定省份/时间范围的交易列表

## 输入参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| keyword | string | 否 | "体育" | 搜索关键词 |
| time_range | string | 否 | "1m" | 时间范围：today/3d/10d/1m/6m |
| page | int | 否 | 1 | 页码（从 1 开始） |
| max_pages | int | 否 | 3 | 最大采集页数 |
| begin_date | string | 否 | "" | 自定义开始日期 YYYY-MM-DD |
| end_date | string | 否 | "" | 自定义结束日期 YYYY-MM-DD |

## 输出结构

```json
{
  "meta": {
    "fetch_time": "2026-03-17T10:00:00",
    "pages_fetched": 3,
    "total_items": 60,
    "total_available": 1598
  },
  "items": [
    {
      "title": "项目名称",
      "publish_date": "2026-03-17",
      "region": "浙江省",
      "platform": "湖州市公共资源交易网",
      "detail_url": "https://www.ggzy.gov.cn/information/deal/html/a/...",
      "business_type": "政府采购",
      "info_type": "采购合同",
      "record_id": "003346ed..."
    }
  ],
  "page_info": {
    "current": 1,
    "total_pages": 80,
    "page_size": 20,
    "total": 1598
  }
}
```

## 调用方式

### 命令行

```bash
# 默认查询（关键词=体育，近一月，前3页）
python tools/ggzy_list_fetch.py

# 自定义查询
python tools/ggzy_list_fetch.py --keyword 医疗 --pages 5 --time-range 10d

# JSON 输出
python tools/ggzy_list_fetch.py --keyword 体育 --json

# 保存到指定文件
python tools/ggzy_list_fetch.py --keyword 体育 --output data/raw/result.json
```

### Python API

```python
from tools.ggzy_list_fetch import fetch_page, fetch_pages, FetchConfig

config = FetchConfig(keyword="体育", time_range="1m")

# 单页采集
result = fetch_page(page=1, config=config)
for item in result.items:
    print(f"{item.title} - {item.publish_date}")

# 多页采集
results = fetch_pages(start_page=1, max_pages=5, config=config)
```

## 数据流

```
用户查询参数
    ↓
ggzy_query_navigator (Skill 调度)
    ↓
ggzy_list_fetch.py (Python 工具)
    ↓
POST https://www.ggzy.gov.cn/information/pubTradingInfo/getTradList
    ↓
JSON 响应 → 结构化 BidListItem[]
    ↓
保存 data/raw/list_fetch_result.json
```

## API 技术细节

- **端点**: `POST https://www.ggzy.gov.cn/information/pubTradingInfo/getTradList`
- **请求格式**: `application/x-www-form-urlencoded`
- **响应格式**: JSON
- **每页条数**: 20
- **重试策略**: 3 次重试，指数退避
- **限流**: 每页间隔 1 秒

## 注意事项

1. 该 Skill 只负责列表页采集，不进入详情页
2. detail_url 可用于后续 Stage2 详情页抽取
3. 所有数据落盘 JSON，不传入 LLM 上下文
4. 平台字段可能为 null，已做空值兼容处理
