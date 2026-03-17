# Stage4 报告 — 数据筛选与报告生成

## 概述

| 项目 | 内容 |
|------|------|
| 阶段 | Stage4: 结构化输出与报告生成 |
| 目标 | 将采集数据导出为 CSV/HTML/JSON 报告 |
| 测试时间 | 2026-03-17 09:54 |
| 状态 | **已封板 (ACCEPTED)** |

## 测试结果

### 封板标准检验 (100 条数据)

| 指标 | 要求 | 实际 | 结果 |
|------|------|------|------|
| 结构化完整率 | ≥ 90% | 100% (100/100) | PASS |
| CSV 生成 | 正常 | 100 行, 6 字段 | PASS |
| HTML 报告 | 正常 | 38KB, 101 行表格 | PASS |
| JSON 导出 | 正常 | 100 条, 含 meta | PASS |

### 输出文件

| 文件 | 大小 | 内容 |
|------|------|------|
| `data/reports/bid_report.csv` | CSV | 100 行, UTF-8-BOM (Excel 兼容) |
| `data/reports/bid_report.html` | HTML | 完整表格报告, 响应式布局 |
| `data/reports/bid_report.json` | JSON | 精简版数据 (不含正文) |

## CSV 字段规格

| 字段 | 来源 | 示例 |
|------|------|------|
| title | 公告标题 | 德清县体育中心...采购项目合同 |
| date | 发布日期 | 2026-03-17 |
| issuer | 采购人/招标人 | 新余市体育事业产业发展中心 |
| region | 省份 | 浙江省 |
| budget | 预算/合同金额 | 1980000.00 元 |
| detail_url | 详情页 URL | https://www.ggzy.gov.cn/... |

## HTML 报告特性

- **响应式布局**: 最大宽度 1200px, 自适应屏幕
- **统计卡片**: 总记录数 / 有效记录 / 覆盖省份 / 含预算信息
- **交互表格**: 鼠标悬停高亮, 长标题 tooltip, 外链跳转
- **视觉设计**: 现代扁平风格, 预算金额橙色高亮, 地区绿色标注
- **编码**: UTF-8, 独立 HTML (无外部依赖)

## 数据流

```
data/structured/bid_data.json
    ↓
export_report.py
    ↓ normalize (日期格式化, 空值处理)
    ├── CSV: data/reports/bid_report.csv
    ├── HTML: data/reports/bid_report.html
    └── JSON: data/reports/bid_report.json
```

## 命令行接口

```bash
# 导出全部格式
python tools/export_report.py --input bid_data --output bid_report

# 仅 CSV
python tools/export_report.py --input bid_data --format csv

# 仅 HTML
python tools/export_report.py --input bid_data --format html
```

## 集成入口

批量采集完成后自动生成报告：

```bash
python tools/ggzy_batch_collect.py --keyword 体育 --pages 5
# 自动输出:
#   data/structured/bid_data.json
#   data/reports/bid_report.csv
#   data/reports/bid_report.html
#   data/reports/bid_report.json
```

可通过 `--no-report` 跳过报告生成。

## 数据质量统计

| 字段 | 填充率 | 说明 |
|------|--------|------|
| title | 100% | 核心字段，全覆盖 |
| date | 100% | 核心字段，全覆盖 |
| detail_url | 100% | 核心字段，全覆盖 |
| region | 100% | 来自列表页 |
| issuer | ~25% | 因公告类型差异 |
| budget | ~35% | 多数类型不含预算 |

## 文件清单

| 文件 | 用途 |
|------|------|
| `tools/export_report.py` | 报告导出工具 |
| `data/reports/bid_report.csv` | CSV 报告 |
| `data/reports/bid_report.html` | HTML 报告 |
| `data/reports/bid_report.json` | JSON 报告 |
| `docs/stage4_report.md` | 本报告 |

## 结论

Stage4 报告生成能力全部通过封板标准（结构化完整率 100%, CSV/HTML/JSON 均正常）。系统全流程交付完成。
