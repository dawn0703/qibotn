# ASC 选拔作业：QiboTN CPU 性能优化

## 提交信息

| 项目 | 内容 |
| --- | --- |
| 姓名 | 张嘉 |
| 年级专业 | 2025级 计算机科学与技术专业 1班 |
| 对应题目 | 大题 4：QiboTN 量子线路模拟优化 |
| 仓库 | https://github.com/dawn0703/qibotn |
| 实验平台 | AutoDL 付费云服务器 |
| 计算设备 | CPU-only |
| 完成情况 | 已完成环境部署、Baseline、正确性验证、4 类优化尝试、最终组合优化与独立复测 |
| 复现方式 | 见本文“基本复现方法”一节及 `asc_homework/scripts/` |
| 最终结果 | 相同 QFT 批处理任务下约 13× 端到端性能提升 |

### 关键结果与证据

- 统一结果表：`asc_homework/results/results.csv`
- 正确性结果：`asc_homework/results/correctness.csv`
- 独立复测结果：`asc_homework/results/final_combined_confirm1.csv`、`asc_homework/results/final_combined_confirm2.csv`
- 任务顺序实验：`asc_homework/results/order_sweep.csv`
- 实验图表：`asc_homework/plots/`
- 环境与运行日志：`asc_homework/logs/`
- 实验与分析脚本：`asc_homework/scripts/`

### 代码与修改说明

本作业未通过修改 QFT 线路定义、删除核心计算或降低问题难度获得性能提升。

本人的主要优化实现位于 `asc_homework/scripts/`，主要包括线程配置、初始化与后端复用、任务调度、进程级并行及实验自动化等 workflow / system-level 改进。

QiboTN 上游核心数值算法源码未作为本作业的主要修改对象。

仓库中用于调研 FDU-SC 公开 `QiboTN-optimized` 方案的脚本和记录仅作为公开先行工作调研与进一步学习方向，不计入本人的原创性能结果。

---


## 1. 题目说明

本仓库用于完成 ASC 选拔作业大题 4：QiboTN 量子线路模拟优化。

实验选择 QFT（Quantum Fourier Transform，量子傅里叶变换）作为主要工作负载，在 CPU-only 条件下测试多个量子比特规模，并从线程配置、初始化复用、任务级并行和任务调度顺序等方向开展性能优化。

实验遵守以下原则：

- 不修改 QFT 线路定义以降低计算难度；
- 不删除核心模拟计算；
- 不使用 GPU；
- 所有性能结果均建立在正确性验证通过的基础上；
- 主要性能结果通过重复实验并使用中位数统计。

## 2. 实验环境

- 云平台：AutoDL 付费实例
- CPU：Intel Xeon Platinum 8481C
- 实际 CPU 配额：25 CPU-equivalents（cgroup）
- 实际内存限制：90 GiB（cgroup）
- 操作系统：Ubuntu 22.04.5 LTS
- Python：3.12.3
- Qibo：0.3.4
- Qibojit：0.1.16
- Quimb：1.15.0
- QiboTN：0.0.7
- 主要后端：QiboTN / Quimb
- 计算设备：CPU
- GPU：机器物理存在 RTX 4090，但本实验未使用

实验通过设置 CUDA_VISIBLE_DEVICES="" 禁用 GPU，Qibo 日志显示计算设备为 /CPU:0。

详细机器和软件环境记录位于 asc_homework/logs/。

## 3. 完成内容

已完成：

- QiboTN CPU 环境部署；
- QFT 基准实验；
- 8、10、12、14、16、18、19 qubits 多规模测试；
- Qibojit 参考结果正确性验证；
- CPU / BLAS 线程数调优；
- 初始化与后端复用；
- 进程级批处理并行；
- 任务执行顺序实验；
- 最终组合优化实验；
- 两轮独立确认实验；
- 峰值内存与扩展性分析；
- 自动化数据汇总、审计和绘图。

## 4. 核心实验结果

| 实验 | 结果 |
|---|---:|
| 19-qubit QFT baseline | 0.438 s |
| 初始化复用 | 4.82x |
| 8 workers 批处理并行 | 4.70x |
| 任务顺序优化 | 约 1.08x |
| 最终组合优化主实验 | 13.81x |
| 独立确认实验 1 | 13.05x |
| 独立确认实验 2 | 13.25x |

最终组合实验使用完全相同的 21 个任务：
QFT(8, 10, 12, 14, 16, 18, 19) × 3。

独立进程串行 baseline 的中位 batch wall time 为约 45.31 s，持久化进程加 8 workers 后降至约 3.28 s。

因此本作业保守报告约 13 倍端到端批处理性能提升。

这里的约 13 倍表示 workflow / batch throughput 的提升，并不表示单个 tensor-network numerical kernel 获得了 13 倍加速。

## 5. 正确性验证

使用 Qibojit CPU state-vector 后端作为参考，对 4、6、8、10 qubits 的 QFT 进行正确性验证。

所有测试均通过，最大绝对误差约为 1e-16 数量级。

原始正确性数据：
asc_homework/results/correctness.csv

Qibojit 在这些小规模测试中的运行时间仅用于生成参考结果，不作为 QiboTN 性能比较依据。

## 6. 数据、图表与脚本

统一结果表：
asc_homework/results/results.csv

主要原始结果：
asc_homework/results/baseline.csv
asc_homework/results/threads.csv
asc_homework/results/reuse.csv
asc_homework/results/batch.csv
asc_homework/results/order_sweep.csv
asc_homework/results/final_combined.csv

实验脚本：
asc_homework/scripts/

图表：
asc_homework/plots/

日志及环境信息：
asc_homework/logs/

## 7. 基本复现方法

推荐使用 Python 3.12，并从仓库根目录执行以下命令。

### 7.1 创建 Python 虚拟环境

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 7.2 安装实验依赖

安装本实验使用的主要 CPU 依赖：

```bash
python -m pip install \
  qibo==0.3.4 \
  qibojit==0.1.16 \
  quimb==1.15.0 \
  pandas==3.0.5 \
  matplotlib==3.11.1 \
  psutil==5.9.8 \
  threadpoolctl==3.6.0
```

安装当前仓库中的 QiboTN：

```bash
python -m pip install -e . --no-deps
```

### 7.3 强制使用 CPU

```bash
export CUDA_VISIBLE_DEVICES=""
```

本实验使用 AutoDL 实例上的 CPU 路径完成所有正式性能测试。机器物理存在 RTX 4090，但评分实验未使用 GPU。

### 7.4 正确性验证

```bash
python asc_homework/scripts/check_correctness.py
```

正确性结果保存在：

```text
asc_homework/results/correctness.csv
```

小规模 QFT 测试中，QiboTN / Quimb CPU 输出与 Qibojit CPU state-vector reference 在双精度浮点误差范围内一致。

### 7.5 Baseline 与主要优化实验

```bash
python asc_homework/scripts/overnight_suite.py
```

该脚本用于执行主要 QFT baseline 及线程配置、初始化复用、批处理并行等实验。

正式测试覆盖：

```text
8, 10, 12, 14, 16, 18, 19 qubits
```

主要性能结果使用重复实验的中位数进行比较。

### 7.6 任务执行顺序实验

```bash
python asc_homework/scripts/order_sweep.py
```

对应结果：

```text
asc_homework/results/order_sweep.csv
```

实验比较 ascending、descending 和 interleaved 三种任务顺序。

### 7.7 最终组合实验

```bash
python asc_homework/scripts/final_combined_suite.py
```

最终组合实验使用相同的 QFT workload 集合重新测量 baseline、persistent process 和不同 worker 数配置，而不是直接将不同优化的局部加速比相乘。

两轮独立复测结果保存在：

```text
asc_homework/results/final_combined_confirm1.csv
asc_homework/results/final_combined_confirm2.csv
```

主实验获得约 13.81× 的端到端批处理加速，两轮独立复测分别约为 13.05× 和 13.25×。

因此本文保守报告约 13× 的端到端 QFT 批处理性能提升。

### 7.8 结果分析与图表生成

重新分析实验结果并生成图表：

```bash
python asc_homework/scripts/analyze_results.py
```

实验图表保存在：

```text
asc_homework/plots/
```

其中包括：

```text
baseline_runtime_vs_qubits.png
threads_vs_runtime.png
reuse_comparison.png
batch_speedup.png
final_combined_runtime.png
memory_vs_qubits.png
```

### 7.9 生成统一结果表

```bash
python asc_homework/scripts/freeze_results.py
```

统一结果表：

```text
asc_homework/results/results.csv
```

该文件汇总 baseline、线程调优、初始化复用、任务级并行、任务顺序和最终组合实验的主要结果。

### 7.10 环境与日志记录

完整实验日志位于：

```text
asc_homework/logs/
```

Python 软件环境记录：

```text
asc_homework/logs/pip_freeze_initial.txt
```

实验脚本位于：

```text
asc_homework/scripts/
```

原始结果位于：

```text
asc_homework/results/
```

因此仓库保留了实验代码、运行命令、环境信息、关键日志、原始结果和最终汇总结果，可用于复现实验过程。

## 8. 公开优秀方案调研与局限性

本实验额外调研了 FDU-SC 公开的 `QiboTN-optimized` 方案，其中包括原生 C++ MPS、Python 热路径下沉、Pauli expectation、缓存以及 Cython 等更深入的优化方向。

FDU-SC 的相关成果仅作为公开先行工作和进一步学习方向，不计入本作业的原创优化结果。

本作业独立完成的主要优化集中在工作流和系统层，包括线程配置、初始化与后端复用、任务调度和任务级并行。

当前实验存在以下局限：

- 按选拔作业要求选择 QFT 作为主要工作负载；
- 当前稠密状态向量重建路径的正式测试规模最大为 19 个量子比特；
- 默认 QFT 全零初态的纠缠较低，对 MPS 表示相对友好；
- 最终约 13 倍提升主要来自工作流和批处理吞吐量优化，而非单个张量网络数值内核；
- 未完整复现 FDU-SC 的 C++ / Cython / MPI 正式竞赛运行环境。

因此，本实验结果不能直接外推到高纠缠的 QAOA、Supremacy 等工作负载。

进一步工作可以从更复杂线路、MPS 键维数、SVD、C++/Eigen、OpenMP、MPI、NUMA、内存带宽和硬件性能计数器等方向继续展开。
