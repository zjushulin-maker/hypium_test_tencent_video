# Hidumper 数据分析工具

这个工具用于解析 `hidumper.txt` 文件，提取 PSS（Proportional Set Size）内存数据，生成饼状图并保存为 Excel 格式。

## 安装依赖

首先需要安装必要的 Python 包：

```bash
pip install pandas matplotlib openpyxl
```

或者使用 requirements 文件：

```bash
pip install -r requirements_analyze.txt
```

## 使用方法

运行脚本会自动处理 `hiperf_output` 目录下所有的 `*hidumper.txt` 文件：

```bash
python analyze_hidumper.py
```

## 输出文件

对于每个 `hidumper.txt` 文件，脚本会生成：

1. **`*_chart.png`** - 饼状图，显示各内存类型的 PSS 分布
   - 每个扇区显示内存类型、大小（MB）和占比（%）
   - 标题显示总 PSS 大小

2. **`*_analysis.xlsx`** - Excel 文件，包含：
   - **PSS数据** 工作表：详细的数据表格
     - 内存类型
     - PSS (kB)
     - PSS (MB)
     - 占比 (%)
   - 饼状图（嵌入在 Excel 中）

## 数据说明

- **PSS (Proportional Set Size)**: 比例集大小，是评估应用内存占用的重要指标
- 数据按 PSS 值从大到小排序
- 饼状图只显示前 15 个最大的内存类型，其余合并为"其他"
- 值为 0 的内存类型会被自动过滤

## 示例

运行脚本后，会在 `hiperf_output` 目录下生成：
- `TencentVideoButton_profiler.hidumper.txt` → 
  - `TencentVideoButton_profiler.hidumper_chart.png`
  - `TencentVideoButton_profiler.hidumper_analysis.xlsx`

