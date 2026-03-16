---
name: environment-bootstrap
description: Automatically repair missing runtime dependencies during task execution. Use when command output shows command not found, ModuleNotFoundError, ImportError, missing CLI tools, or missing Python libraries.
---

# Environment Bootstrap

## Purpose

在任务执行过程中，如果因为本地环境缺失依赖导致失败，自动补齐最小依赖后继续任务，而不是立即中断等待用户手工安装。

## Auto-Trigger Signals

出现以下信号时，优先触发本 Skill：

- shell 输出包含 `command not found`
- Python 输出包含 `ModuleNotFoundError` 或 `ImportError`
- 任务明确依赖常见命令（如 `vim`、`wget`、`telnet`）但当前不可用

## Workflow

1. **识别缺失项**
   - 从错误日志中提取缺失命令或缺失 Python 包名。
2. **先检测再安装**
   - 命令：`command -v <cmd>`
   - Python 包：`python3 -c "import <module>"`
3. **自动安装最小依赖**
   - 系统命令缺失：`apt-get update && apt-get install -y <apt-package>`
   - Python 包缺失：`python3 -m pip install <pip-package>`
4. **安装后验证**
   - 命令验证：`command -v <cmd>`
   - Python 验证：`python3 -c "import <module>"`
5. **继续原任务**
   - 回到失败前步骤继续执行，不重复做无关动作。

## Mapping Hints

以下映射是**常见示例**，用于提升命中率，**包括但不限于**这些项。  
不要把此列表当作白名单；遇到未列出的缺失项时，仍应按“识别 -> 检测 -> 安装 -> 验证”流程自动处理。

- `vim` -> `vim`
- `wget` -> `wget`
- `telnet` -> `inetutils-telnet`
- `ifconfig` -> `net-tools`
- `dig` -> `dnsutils`
- `nslookup` -> `dnsutils`
- `ping` -> `iputils-ping`
- `ss` -> `iproute2`
- `openpyxl` -> `openpyxl`
- `yaml` 模块缺失通常对应 `PyYAML`
- `cv2` 模块缺失通常对应 `opencv-python`
- `PIL` 模块缺失通常对应 `pillow`
- `bs4` 模块缺失通常对应 `beautifulsoup4`
- `sklearn` 模块缺失通常对应 `scikit-learn`
- `Crypto` 模块缺失通常对应 `pycryptodome`
- `lxml` 模块缺失通常对应 `lxml`
- `xlsxwriter` 模块缺失通常对应 `XlsxWriter`
- `dateutil` 模块缺失通常对应 `python-dateutil`
- `dotenv` 模块缺失通常对应 `python-dotenv`

## Mapping Priority

- 映射表是示例集，不是完整清单；未命中的项必须继续泛化处理。
- 优先使用社区通用且维护稳定的包名。
- 当 import 名与 pip 名不一致时，按上面的映射优先处理。
- 若无法确定映射，先执行最小探测（例如 `python3 -m pip index versions <name>` 或等效方法），再安装。
- 当多个候选都可能可用时，先安装最小依赖路径，并用实际导入/命令校验结果作为最终依据。

## Guardrails

- 仅安装当前任务必需的依赖，避免大范围安装。
- 不执行系统升级类命令（如 `apt upgrade`、`dist-upgrade`）。
- 遇到安装失败时，输出清晰诊断（包名、命令、错误摘要）并给出下一步建议。
- 若有多个可选包，优先选择最常见、最小可用方案。

## Example

当错误为：

`ModuleNotFoundError: No module named 'openpyxl'`

应自动执行：

`python3 -m pip install openpyxl`

并验证：

`python3 -c "import openpyxl; print(openpyxl.__version__)"`
