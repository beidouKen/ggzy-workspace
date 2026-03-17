# Stage3 报告 — 批量采集与上下文控制

## 概述

| 项目 | 内容 |
|------|------|
| 阶段 | Stage3: 批量采集能力 |
| 目标 | 列表页 → 详情页 → 结构化 JSON 全流程 |
| 测试时间 | 2026-03-17 09:50 |
| 状态 | **已封板 (ACCEPTED)** |

## 测试结果

### 封板标准检验 (max_pages=5)

| 指标 | 标准 | 实际 | 结果 |
|------|------|------|------|
| 采集条数 | ≥ 50 | 100 | PASS |
| 成功率 | ≥ 90% | 100% (100/100) | PASS |
| 重复率 | < 5% | 0% (0/100) | PASS |
| 结构化输出 | 有效 JSON | 有效 | PASS |

### 详细统计

| 指标 | 值 |
|------|-----|
| 搜索关键词 | 体育 |
| 列表页采集 | 5 页 |
| 总可用记录 | 1,598 条 |
| 实际处理 | 100 条 |
| 成功 | 100 条 |
| 失败 | 0 条 |
| 去重移除 | 0 条 |
| 最终存储 | 100 条 |
| 耗时 | 119.2s |

## 架构设计

### 三阶段流水线

```
Phase 1: 列表页采集
  ggzy_list_fetch.py → POST API → BidListItem[]
  ├── 5 页 × 20 条/页 = 100 条
  └── 增量去重: 跳过已有 record_id

Phase 2: 详情页抽取
  ggzy_detail_fetch.py → A-page + B-page → DetailResult
  ├── 批处理: 每 10 条为一批
  ├── 每批落盘: data/raw/{name}_batch_{n}.json
  └── 失败容错: 记录 error 字段，不中断流程

Phase 3: 合并存储
  合并新旧数据 → record_id 去重 → data/structured/{name}.json
```

### 批处理策略

| 参数 | 值 | 说明 |
|------|-----|------|
| 批大小 | 10 | 每 10 条详情采集后落盘 |
| 列表页间隔 | 1.0s | 防 API 限流 |
| 详情页间隔 | 1.0s | 防页面限流 |
| 重试次数 | 3 | 指数退避 |
| 去重机制 | record_id | 增量采集 |

### 数据存储

| 路径 | 格式 | 说明 |
|------|------|------|
| `data/raw/{name}_list.json` | JSON | 列表页原始数据 |
| `data/raw/{name}_batch_{n}.json` | JSON | 每批详情页数据 |
| `data/structured/{name}.json` | JSON | 合并去重后结构化数据 |

## 字段采集率统计 (100 条样本)

| 字段 | 采集率 | 说明 |
|------|--------|------|
| title | 100% | 所有记录均有 |
| publish_date | 100% | 所有记录均有 |
| content_text | 98% | 2 条内容极短 |
| region | 100% | 来自列表页 |
| record_id | 100% | 来自列表页 |
| issuer | ~25% | 因公告类型差异 |
| budget | ~35% | 多数类型无预算信息 |
| attachments | ~15% | 仅部分公告含附件 |

## 增量采集能力

工具支持增量模式：
- 第一次运行：全量采集 100 条
- 重复运行：自动跳过已采集的 record_id
- 合并逻辑：新数据追加到现有 JSON，再按 record_id 去重

## 容错机制

| 场景 | 处理方式 |
|------|----------|
| 详情页请求失败 | 3 次重试 + 指数退避，失败后记录 error 字段 |
| B-page URL 缺失 | 返回仅含 A-page 元数据的结果 |
| 网络超时 | 15 秒超时，自动重试 |
| 中间批次失败 | 不影响后续批次，已成功数据已落盘 |

## 潜在风险

| 风险 | 等级 | 说明 |
|------|------|------|
| 高频触发限流 | 中 | 目前 1s 间隔稳定，高并发可能受限 |
| 验证码机制 | 中 | API 返回 code=829 时需验证码，当前未遇到 |
| 大批量内存 | 低 | 每批落盘，不会积累大量内存 |
| 字段格式变更 | 低 | 不同省份页面格式差异，正则容错处理 |

## 文件清单

| 文件 | 用途 |
|------|------|
| `tools/ggzy_batch_collect.py` | 批量采集核心工具 |
| `skills/ggzy_batch_collector.md` | OpenClaw Skill 文档 |
| `tests/test_stage3_batch_collect.py` | 自检脚本 |
| `data/structured/stage3_test_data.json` | 结构化采集数据 |
| `data/raw/stage3_test_data_list.json` | 列表页原始数据 |
| `data/raw/stage3_test_data_batch_*.json` | 批次详情数据 (10 文件) |
| `data/raw/stage3_test_log.txt` | 测试日志 |
| `data/raw/stage3_test_result.json` | 测试结果 |
| `docs/stage3_report.md` | 本报告 |

## 结论

Stage3 批量采集能力全部通过封板标准（100 条/100% 成功率/0% 重复率），支持增量采集和容错恢复。可进入 Stage4。
