# 腾讯视频 HarmonyOS UI 自动化压测框架

基于 xdevice / Hypium 的腾讯视频 HarmonyOS 应用 UI 自动化压测工具，支持多用例遍历、多轮次循环、设备异常自动采集。

---

## 目录结构

```
hypium_test_tencent_video/
├── main.py                          # 压测主入口
├── testcases/
│   ├── TencentVideoBase.py          # 测试基类（公共逻辑）
│   ├── TencentVideoHome.py          # 用例：首页滑动
│   ├── TencentVideoButton.py        # 用例：首页 Tab 切换
│   ├── TencentVideoShort.py         # 用例：短视频滑动
│   ├── TencentVideoComment.py       # 用例：评论区滑动
│   ├── TencentVideoComprehensive.py # 用例：综合场景
│   └── *.json                       # 各用例对应的 xdevice 配置文件
├── aw/
│   └── Utils.py                     # 公共工具函数
├── reports/                         # 测试报告输出目录（自动创建）
└── faultlogs/                       # 设备 faultlog 保存目录（自动创建）
```

---

## 环境依赖

| 依赖 | 说明 |
|---|---|
| Python 3.x | 建议 3.9+ |
| xdevice | HarmonyOS 测试框架，`pip install xdevice` |
| Hypium | HarmonyOS UI 自动化库，随 DevEco Testing 安装 |
| hdc | HarmonyOS 设备连接工具，需在 PATH 中可用 |

确认 hdc 可用：

```bash
hdc list targets
```

---

## 快速开始

### 1. 连接设备

```bash
hdc list targets
```

### 2. 运行压测

```bash
# 使用默认配置（100 轮，自动选择当前连接设备）
python main.py

# 指定轮数和设备 SN
python main.py -r 50 -sn ABCD1234EFGH

# 无限循环直到手动停止（Ctrl+C）
python main.py -r 0

# 多台设备（SN 用 ; 分隔）
python main.py -sn ABCD1234;EFGH5678

# 自定义报告和 faultlog 保存目录
python main.py -rp ./my_reports -fp ./my_faultlogs
```

---

## 命令行参数

| 参数 | 简写 | 默认值 | 说明 |
|---|---|---|---|
| `--repeat` | `-r` | `100` | 压测总轮数；`0` 为无限循环 |
| `--device-sn` | `-sn` | （当前连接设备） | 指定设备 SN，多台用 `;` 分隔 |
| `--report-path` | `-rp` | `reports` | xdevice 测试报告输出目录 |
| `--fault-path` | `-fp` | `faultlogs` | 设备 faultlog 本地保存目录 |

---

## 测试用例说明

每个用例均继承自 `TencentVideoBase`，执行流程为：

```
强制退出 App → 启动 App → 跳过广告 → [用例主体操作] → 关闭 App
```

| 用例文件 | 场景描述 | 基准操作量 | 压测操作量（×50） |
|---|---|---|---|
| `TencentVideoHome` | 首页上下滑动 | 50 次滑动 | 2500 次 |
| `TencentVideoButton` | 首页 Tab 来回切换 | 3 轮切换 | 150 轮 |
| `TencentVideoShort` | 短视频上划切换 | 30 次滑动 | 1500 次 |
| `TencentVideoComment` | 进入视频评论区上划 | 60 次滑动 | 3000 次 |
| `TencentVideoComprehensive` | Tab 切换 + 视频滑动 + 评论滑动 | 20+50 次 | 1000+2500 次 |

---

## 压测倍率配置

所有用例的操作次数由 `TencentVideoBase.py` 顶部的 `STRESS_MULTIPLIER` 常量统一控制：

```python
# testcases/TencentVideoBase.py
STRESS_MULTIPLIER = 50   # 1 = 正常模式，50 = 压测模式
```

修改此值后，所有用例的操作次数同步生效，无需逐个修改。

---

## 设备异常采集

每轮压测结束后，脚本会自动：

1. 对比本轮开始前后设备 `/data/log/faultlog/faultlogger/` 目录的差异
2. 过滤与 `com.tencent.videohm` 相关的异常文件（`cppcrash`、`appfreeze`、`jscrash`、`sysfreeze`）
3. 通过 `hdc file recv` 将新增文件拉取到本地
4. 在终端打印醒目的红色告警

本地保存路径结构：

```
faultlogs/
└── round_0001/
│   ├── cppcrash-com.tencent.videohm-xxxxx
│   └── appfreeze-com.tencent.videohm-xxxxx
└── round_0002/
    └── ...
```

---

## 运行输出示例

```
发现用例（共 5 个）：['TencentVideoButton', 'TencentVideoComment', ...]
压测轮数：100
设备 SN ：ABCD1234EFGH
报告目录：reports
故障日志：faultlogs

───────────────────────────────────────────────────────
  第    1 轮 / 100
───────────────────────────────────────────────────────

# 用例失败时打印：
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
  ✖  用例失败告警
  时间：2026-05-19 10:23:45
  轮次：第 1 轮
  用例：TencentVideoComment
  详情：...
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

# 发现 faultlog 时打印：
★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
  ⚠  设备异常告警（新增 faultlog）
  时间：2026-05-19 10:25:01
  轮次：第 1 轮
  共发现 1 个新问题文件：
    → faultlogs/round_0001/cppcrash-com.tencent.videohm-12345
★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
```

---

## 进阶功能

### 内存监控（pmap）

`TencentVideoBase` 内置 pmap 后台采样线程，默认**关闭**。如需启用：

```python
# testcases/TencentVideoBase.py
self.enable_memdump = True   # 启用 GC dump 触发与下载
```

采样数据保存在 `dump_output/<CaseName>_memdump.log`，包含 `anon:Kotlin` 虚拟内存和物理内存时序数据。

### Profiler（hiprofiler）

```python
self.enable_profiler = True  # 启用 hiprofiler native hook 采集
```

htrace 文件保存在 `hiperf_output/<CaseName>_profiler.htrace`。

---

## 停止压测

运行中按 `Ctrl+C` 可随时优雅停止，脚本会打印已完成轮数后退出。

```
压测已手动停止，共完成 23 轮

═══════════════════════════════════════════════════════
  压测完成 · 共 23 轮
═══════════════════════════════════════════════════════
```
