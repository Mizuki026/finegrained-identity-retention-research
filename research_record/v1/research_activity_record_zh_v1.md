# 细粒度身份属性保持研究：中文全过程记录 v1

## 文档用途与存放边界

本文件是从研究者于 2026-08-03 发出“自主推进至论文初稿”指令起的中文可审计记录源文件。其 Word 快照由同目录的版本化 DOCX 生成。当前 Linux 工作环境不能访问 `E:\Scientific research\Scientific record`；完成的 `.docx` 将保存在本仓库，供研究者复制到该 Windows 路径。

本记录不以叙事替代机器可读证据。每一项结果、数字、图和论文句子都必须能回溯到具体 artifact、SHA256、产生脚本、Git commit、输入 lineage 与预先冻结的协议。

## 术语与证据规则

| 标记 | 含义 | 写作约束 |
|---|---|---|
| 事实 | 可由 hash、冻结 artifact 或可复现运行直接验证 | 不延伸为科学因果结论 |
| 诊断 | 工程或测量系统信号 | 不等于属性缺失或科学效应 |
| 推断 | 基于证据的解释 | 必须写清局限与替代解释 |
| 假说 | 未来可检验命题 | H1–H4 均仍属此类 |
| 研究决定 | 研究者授权的设计或范围选择 | 必须记录授权、时间和后果 |

## 已完成工作（截至本记录建立前）

1. **研究治理与可复现基础设施（事实）**：独立仓库 `research_pipeline` 已建立；上游 `code/ConsisID` 保持只读且干净；frozen manifest、config、metric specs、reference audits、generation metadata 与日志均已登记。
2. **canonical config 更正（事实）**：权威 `config.json` SHA256 是 `40014634ef08f17eae3bf41b4d551796efe3855fc7f25c8d3f9b66d9f0e7ef47`。手写 65 位版本是 transcription error，未修改任何既有 artifact。
3. **Stage 1 输出完整性审计（事实）**：12 个 frozen MP4 全部由 OpenCV 与 Decord 以 CPU 完整解码；每个 49 帧、8 FPS、720×480、6.125 秒。审计为 12/12 PASS。
4. **Stage 1 异常诊断（诊断）**：黑帧、损坏帧、精确/近重复转移、冻结段与静态异常均为零。该诊断仅说明未发现协议定义的粗粒度技术损坏。
5. **独立复核（事实）**：独立 no-decode verifier 核对了样本集合、路径、SHA256、schema、588 个帧记录、状态聚合、checksum manifest 与 contact sheet PNG 结构，返回 PASS。
6. **不可作出的结论（研究决定）**：上述完整性审计没有衡量 identity、eyeglasses、facial hair 或 hair color；不得把它写成 H1–H4 的证据。

## 本轮重新授权

| 项目 | 记录 |
|---|---|
| 研究者指令 | 自 2026-08-03 起，在既有规范下自主推进，直至论文初稿完成 |
| Gate 含义 | 视为接受 Human Gate A 的完整性证据，并授权开始后续治理、评价计划、证据组织与论文基础设施 |
| 保留的高风险约束 | GPU/模型加载、联网、安装、重新生成、正式大规模实验、probe/intervention、改变冻结设计或主要结论仍需在实际触发前记录明确 gate 决定 |
| 当前科学状态 | H1–H4 未检验；reference audit 仅支持参考集可用性；Pilot 的 12 个视频高度受身份、属性和历史图像域混杂限制 |

## 从现在到论文初稿的工作路径

1. 冻结 Pilot 属性评价执行协议、帧抽样与统计分析计划；不查看属性结果后倒改阈值、标签或主分析。
2. 在明确模型/人工标注/计算授权后，运行全样本属性与可观测性评价；保留 missing、unobservable、pipeline failure 与 attribute absence 的区别。
3. 以 Pilot 为可行性与效应量探索，而非确认性结论；决定正式研究时先冻结样本、配对、排除、停止规则、统计模型与预算。
4. 对正式研究建立 generation、integrity、attribute、quality-control 和分析的端到端 lineage；不选择性删样或重生成。
5. 建立论文 claim–evidence 对照、每个数字/图的 CSV 和脚本索引、引用核验表、图表代码与 SHA256。
6. 仅在证据边界允许的语言下撰写论文初稿；明确 Pilot 的限制、混杂、相关帧问题和不可作出的机制结论。

## 必须持续维护的论文可追溯账本

| 账本 | 论文中回答的问题 | 最低字段 |
|---|---|---|
| claim–evidence 对照表 | 每一句主要结论凭什么成立、允许说到何种强度 | claim_id、证据类别、artifact、SHA256、脚本、样本、统计边界、允许措辞 |
| number provenance 表 | 每个数字来自何处 | manuscript_location、number_id、CSV、列/行、生成脚本、SHA256、commit |
| figure/table registry | 每张图表能否被独立复现 | figure_id、输入 CSV、脚本、输出、SHA256、caption、统计口径 |
| artifact registry | 输入与 derived 输出有无完整 lineage | artifact_id、父 artifact、immutable、路径、SHA256、状态 |
| citation verification 表 | 每个引用是否存在、是否直接支持对应陈述 | citation_key、原始链接/DOI、核验日期、支持句、证据级别、限制 |
| research activity record | 从授权到初稿期间具体做了什么 | 时间、阶段、目的、输入、输出、验证、失败、gate、风险 |

## Stage 1 已有核心证据索引

| Artifact | SHA256 | 用途 |
|---|---|---|
| `derived/pilot_v1_1/video_integrity_audit_v1/video_integrity_audit_v1.csv` | `a762dcf9d3b85334d557fbdb223594689d926b7f4e8e703f3432f17911c118d5` | 12 个视频的路径、哈希、解码与 PASS/FAIL 证据 |
| `derived/pilot_v1_1/video_integrity_audit_v1/frame_inventory_v1.csv` | `a6f74cf8a7013f7bc621bc71de3c22609e91b21a290f3b2d1c2ba082a2524c27` | 588 个帧的工程诊断记录 |
| `derived/pilot_v1_1/video_integrity_audit_v1/pilot_output_audit_v1.json` | `616373e6e5e63e039ac3fabc12c09fe8f1eff0d47f850de4ae32b7740be1fc32` | Pilot 工程完整性汇总 |
| `derived/pilot_v1_1/video_integrity_audit_v1/independent_verification_v1.json` | `12075e958cf16c6345be5f3d46a024fcedc91e8a4cbe9f8c1f62faf128ae2b83` | 独立 no-decode 复核 |
| `governance/video_integrity_audit_protocol_v1.md` | `5012d924f3ee5b35b45dc8538791b67a6d08a377b18301a9266105bd8f37bbb0` | Stage 1 冻结规则 |

## 后续更新规则

- 每完成一个阶段，创建新的 `research_record/vN/` 快照；不覆盖已发布版本。
- 每个快照同时保留 Markdown 源、DOCX、生成 log 和 input/output SHA256 manifest。
- 每个阶段在 `WORKLOG.md`、`NEXT_ACTION.md`、claim ledger、human gate log 和 artifact registry 留下对应记录。
- 论文初稿完成时，生成最终中文全过程记录，逐项列出 claim、数字、图、表、引用与 artifact lineage。

## 当前停点

当前处于“后续研究治理与评价计划冻结”阶段。尚未运行属性指标、未加载模型/GPU、未使用网络、未安装依赖、未重新生成视频，也未开始正式实验或机制研究。
