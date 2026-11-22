# 评测

[English](../EVALUATION.md)

eyeful 的评测方案。方案依照 eyeful 的
[proposal](https://github.com/Pleasurecruise/eyeful/blob/main/docs/reports/proposal.pdf)；所有偏离都按日期记录在
[`registry/amendments.md`](../../registry/amendments.md)。对设计的修改都在任何审查评分之前做出；之后的条目不改变任何结果。结果见 [RESULTS.md](RESULTS.md)。

## 1. 研究问题

研究问题沿用已冻结的 proposal。RQ1 和 RQ2 问的是 planner 与验证器如何构建；评测回答 RQ3，并用一个消融检验每项设计。

| 问题          | proposal 原文                                                                                                        | 测量方式                                                           |
| ------------- | -------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| RQ1，规划     | How can a change be divided among expert agents so that every changed file is reviewed by the experts its intent needs? | planner 消融：用两个固定专家替换 planner                           |
| RQ2，验证     | How can a candidate finding be confirmed by execution when the expected behaviour may not be stated in the code?       | finding 走完六道关卡的比例；oracle 规则消融：任何复现都可阻塞     |
| RQ3，评测     | Does the panel find more known defects than a single agent with the same model and skills, does verification leave fewer invalid findings, and at what cost? | 检出（召回率）、噪声（各条件下的精确率）和成本                    |

## 2. 基准与抽样

缺陷必须事先已知，这样任何输出都不用人工标注；并且至少要有一个基准的测试可以运行。没有任何 subject 用于 eyeful 的 prompt 开发。

| 基准               | 来源                                                                                                  | 已知缺陷                               | subject 数 | 测量                   |
| ------------------ | ----------------------------------------------------------------------------------------------------- | -------------------------------------- | ---------- | ---------------------- |
| SWE-bench Verified | [SWE-bench/SWE-bench_Verified](https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified)          | issue 本身，由隐藏测试判定             | 30         | 检出、可验证性、成本   |
| Code Review Bench  | [withmartian/code-review-benchmark](https://github.com/withmartian/code-review-benchmark) 的离线数据集 | Core 类别的 golden comment，经人工确认 | 10         | 检出、噪声、成本       |
| ReviewBench        | [review-bench/ReviewBench](https://github.com/review-bench/ReviewBench)                                | 被接受的 golden finding                | 50         | 确认性实验，2027 年 2 月 |

**SWE-bench。** 抽样框是评测装置能运行测试的 7 个项目中的 293 道题。16 个 subject 来自一组 20 个的目的性样本，其中 4 个不满足有效性标准（§3）；另外 14 个按题号 SHA-256 的顺序抽取（[`selection.md`](../../registry/swebench/selection.md)）。
**Code Review Bench。** 离线数据集中的 10 个 Keycloak pull request；eyeful 的 prompt 开发时用过的 7 个 pull request 来自其他项目。**ReviewBench。** 从 219 个中去掉开发用过的 25 个后抽取 50 个，在主要结果之后作为确认性实验运行（[`plan.md`](../../registry/reviewbench/plan.md)）。

## 3. 测试对象

一个 subject 是一个含 base 和 head 两个 commit 的 git 仓库，eyeful 审查 head。

- **SWE-bench（撤销修复）。** 从题目的镜像构建：base 提交官方修复，head 撤掉修复，所以被审查的改动会引入这道题的 issue。提供两个测试命令：一个跑单个测试，一个跑由能通过的 PASS_TO_PASS 测试组成的回归套件，都在题目镜像里断网运行。
- **Code Review Bench 与 ReviewBench。** pull request 的 head，相对其 base 与 head 的 merge base。
- **盲化。** 缺陷描述和仓库分开存放，名字都是哈希，隐藏测试永远不进入仓库。
- **有效性。** SWE-bench subject 保留的条件是：隐藏测试在断网环境下 base 上通过、head 上失败，并且回归套件非空。这只检验环境，不涉及任何审查。

## 4. 实验设计

被试内设计，两个因素。

| 配置   | 运行方式                             | 重复次数 | 由谁来找                       |
| ------ | ------------------------------------ | -------- | ------------------------------ |
| panel  | `eyeful review`                      | 1        | planner 分配的专家             |
| single | `eyeful review generalist`           | 3        | 一个拥有全部 skill 的 agent    |
| fixed  | `eyeful review correctness security` | 1        | 两个专家，无 planner（消融）   |

| 验证条件  | 报告哪些 finding                       | SWE-bench       | Code Review Bench       |
| --------- | -------------------------------------- | --------------- | ----------------------- |
| execution | 被复现的；无法测试时，未被驳回的       | 是              | 是，等同于 read_only    |
| read_only | judge agent 不驳回的                   | 否：测不出噪声  | 是                      |
| none      | 全部                                   | 是              | 是                      |

panel 与 single 三次重复的并集比较（三次的成本与 panel 一次相近），也与 single 的第一次比较。execution 负责找 finding，其他条件验证同一批 finding，所以条件之间的差异只来自验证。构建版本、模型、推理档位、skill、提示词、预算和测试命令保持不变。分析单位是 subject。

## 5. 评测装置

[`eval/`](../../eval) 每个阶段一个包。每个阶段只依赖 `core`（其中 `layout` 规定阶段之间交换的文件）和上一阶段写下的文件；`review` 另经 `record` 写下本次运行的 manifest。每个包的测试在 `eval/tests/test_<包名>.py`。

| 包         | 职责                                                         |
| ---------- | ------------------------------------------------------------ |
| `build`    | 构建 subject，检验其有效性（§3），按规则抽取 SWE-bench 与 ReviewBench subject |
| `review`   | 在沙箱中逐个完成审查并重试；审计越界访问；读取 finding 和验证结果 |
| `record`   | 每次运行的 manifest；进度表                                  |
| `score`    | 各基准自带的评分：SWE-bench 官方 harness、两个审查基准的 judge |
| `analysis` | 指标和置信区间                                               |
| `core`     | 共用的记录结构；阶段之间交换的文件；运行命令                 |

[`eval/schedule.sh`](../../eval/schedule.sh) 按固定顺序运行整个实验。

## 6. 实验流程

- **模型。** 所有 agent 和 judge 都通过 pi 使用 OpenCode Go 上的 DeepSeek V4.1 Flash，推理档位 `medium`。
- **顺序。** 一次只进行一个审查：服务方最多允许 20 个并发调用，一次审查最多发出 8 个。
- **隔离。** agent 只能读取被审查的仓库。有任何其他访问的审查被排除，验证其专家 finding 的条件也一并排除。
- **失败。** 失败的审查最多重试 3 次，仍失败则记为 failed，视为什么都没找到。
- **溯源。** manifest 记录固定条件和每次调用，包括脚本的哈希。

## 7. 测量

| 基准              | 缺陷算作检出                                                  | finding 有效                  | 评分脚本     |
| ----------------- | ------------------------------------------------------------- | ----------------------------- | ------------ |
| SWE-bench         | 官方 harness 判定某条报出 finding 的修复解决了原题            | 它的修复解决了原题            | `resolve.py` |
| Code Review Bench | benchmark 的 judge 把某条 finding 匹配到 Core golden comment | judge 没有判它为误报          | `match.py`   |
| ReviewBench       | benchmark 的 judge 认定某条 finding 覆盖一条被接受的 golden finding | judge 判它为真阳性 | `score/reviewbench.py` |

RQ3：召回率和类别数，McNemar 精确检验；各条件下的精确率，配对 bootstrap；token、费用和时间，bootstrap。RQ2：执行过的 finding 中走完全部六道关卡的比例、能解决原题但执行没能确认的 finding，以及有无 oracle 规则时可阻塞的 finding。RQ1：planner 消融的召回率，McNemar 精确检验。置信区间为 95%，来自对 subject 的 10,000 次重抽样；抽样前先按固定顺序排列，使种子唯一决定结果。

## 8. 有效性威胁

- **构念。** golden 集合不完整，精确率只是下限。SWE-bench 上改动本身就是缺陷，测不出噪声；而且只有执行复现过的 finding 才可能有效，所以验证损失按定义恒为零。Code Review Bench 的 subject 没有可运行的测试，execution 在此等同于 read_only：测到的只是只读 judge 能否降噪，执行验证能否降噪没有被测量。
- **内部。** 同一个模型担任审查者、judge 和评分者；judge 可能偏宽松，且不同次结果不同；重试保留成功的那次。运行期间修改过记录结果的脚本，但从未修改执行审查的构建，每次修改都在 manifest 中可查。
- **开发。** eyeful 的 prompt 曾在样本之外的 7 个 Code Review Bench pull request 上调整，其中两句对照 golden comment 写下的措辞不在被评测的构建中。在方案修订之前，已有 7 个被抽中的 Code Review Bench subject 和 2 个 SWE-bench subject 的试跑审查被人工阅读过。
- **外部。** subject 都是 Python 项目，大多来自 Django；另有 10 个 Keycloak pull request；模型可能见过 SWE-bench 的 issue。
- **统计结论。** proposal 计划约 130 个 subject、860 次审查；时间只允许 40 个 subject、456 次审查，panel 只跑一次。统计效力有限，没有显著差异不等于等价。开发中未用过的 ReviewBench 将于 2027 年 2 月作为确认性实验运行。
