# Skill: ggzy_batch_collector

## 用途

批量采集全国公共资源交易平台（ggzy.gov.cn）招标信息，自动完成列表页采集 → 详情页抽取 → 结构化存储的全流程。

## 触发条件

当用户需要：
- 批量采集某关键词的招标/采购公告
- 导出一批结构化招标数据（含详情）
- 定期更新采集数据（增量模式）

## 输入参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| keyword | string | 否 | "体育" | 搜索关键词 |
| max_pages | int | 否 | 5 | 最大列表页数 |
| time_range | string | 否 | "1m" | 时间范围：today/3d/10d/1m/6m |
| delay_list | float | 否 | 1.0 | 列表页间隔（秒） |
| delay_detail | float | 否 | 1.0 | 详情页间隔（秒） |
| output_name | string | 否 | "bid_data" | 输出文件名前缀 |

## 输出结构

```json
{
  "meta": {
    "keyword": "体育",
    "last_fetch_time": "2026-03-17T10:00:00",
    "total_items": 95,
    "total_available": 1598,
    "pages_fetched": 5
  },
  "items": [
    {
      "title": "公告标题",
      "publish_date": "2026-03-17 00:00",
      "region": "浙江省",
      "issuer": "某体育局",
      "agency": "某咨询公司",
      "budget": "198万元",
      "content_text": "正文...",
      "attachments": [{"name": "招标文件.pdf", "url": "https://..."}],
      "record_id": "003346ed...",
      "business_type": "政府采购",
      "info_type": "采购合同"
    }
  ]
}
```

## 调用方式

### 命令行

```bash
# 默认采集（关键词=体育，5页）
python tools/ggzy_batch_collect.py --keyword 体育 --pages 5

# 自定义参数
python tools/ggzy_batch_collect.py --keyword 医疗 --pages 10 --time-range 10d --delay-detail 1.5

# 自定义输出文件名
python tools/ggzy_batch_collect.py --keyword 体育 --output sports_data
```

### Python API

```python
from tools.ggzy_batch_collect import batch_collect

stats = batch_collect(keyword="体育", max_pages=5, time_range="1m")
print(f"Success: {stats['success']}/{stats['items_processed']}")
```

## 数据流

```
用户参数
    ↓
ggzy_batch_collector (Skill 调度)
    ↓
ggzy_batch_collect.py (Python 工具)
    ↓
Phase 1: ggzy_list_fetch.py → 列表页 API → BidListItem[]
    ↓  (去重: 跳过已采集 record_id)
Phase 2: ggzy_detail_fetch.py → 详情页 HTML → DetailResult[]
    ↓  (每批 10 条, batch 中间落盘)
Phase 3: 合并 + 去重 → data/structured/bid_data.json
```

## 批处理策略

| 参数 | 值 | 说明 |
|------|-----|------|
| 每批条数 | 10 | 每 10 条详情采集后落盘一次 |
| 列表页间隔 | 1.0s | 防止列表 API 限流 |
| 详情页间隔 | 1.0s | 防止详情页限流 |
| 重试次数 | 3 | 每个请求最多重试 3 次 |
| 去重机制 | record_id | 增量采集时跳过已有记录 |

## 输出文件

| 路径 | 格式 | 说明 |
|------|------|------|
| `data/raw/{name}_list.json` | JSON | 列表页原始数据 |
| `data/raw/{name}_batch_{n}.json` | JSON | 每批详情页原始数据 |
| `data/structured/{name}.json` | JSON | 合并去重后的结构化数据 |

## 注意事项

1. Skill 只负责调度，实际解析由 Python 工具完成
2. 所有数据落盘 JSON，正文不传入 LLM 上下文
3. 支持增量采集：重复运行时自动跳过已采集的 record_id
4. 采集失败的条目仍会记录（含 error 字段），不影响后续处理
