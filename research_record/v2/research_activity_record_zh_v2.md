# 细粒度身份属性保持研究：中文全过程记录 v2

## v2 的定位

本文件是 v1 的不可覆盖续篇，记录 Human Gate A 被接受以后至 Pilot 属性结果执行之前的全部工作。v1 的 Markdown、DOCX 与生成日志保持不变；v2 不替代也不修改 v1。

## 阶段 A：重新授权与证据边界

| 项目 | 分类 | 已完成的工作 | 可作出的结论 | 不可作出的结论 |
|---|---|---|---|---|
| Human Gate A | 研究决定 | 研究者授权自主推进至论文初稿；该授权已写入 gate log 的 D011/T006 | Stage 1 的工程完整性已被人类接受 | 属性、身份、机制或 H1-H4 没有因此成为发现 |
| 安全约束 | 研究决定 | 保留模型/GPU、网络/安装、重新生成、正式实验、probe/intervention、冻结设计变更和盲法人工标注的单独 gate | 可以自主完成治理、代码准备、证据组织和论文基础设施 | 不可以把一般性自主授权解释为任何模型或正式实验的无条件许可 |
| Windows 记录位置 | 事实 | 当前 Linux 运行环境未挂载 E:\\Scientific research\\Scientific record | 版本化 DOCX 可从 research_pipeline 导出/复制 | 不能声称已直接写入研究者 Windows 磁盘 |

## 阶段 B：中文记录与 Word 快照

| Artifact | SHA256 | 事实 |
|---|---|---|
| research_activity_record_zh_v1.md | fba3460304f880a1274757c5e1255bda47c812739fcd80a2967cf25eb3aeb3c5 | 中文可审计源文件已建立 |
| research_activity_record_zh_v1.docx | 35cbfeb539da83e010ab5117c0e210fe410ac29c216ca822ce63761ec76283a0 | 本地 Office Open XML 快照生成并通过 ZIP 结构核验 |
| research_activity_record_docx_v1_run_log.json | 0bb3f097198879e54a8c221f5aa61f42347801c5747c28531dca02c29d59f1d7 | 记录 source/output 哈希与 CPU-only、无网络、无模型状态 |

生成 Word 快照没有安装依赖，也没有读取任何 frozen 图像、视频、模型或网络资源。生成器为标准库脚本，版本 hash 为 2d0afdf70de812afa9ac025ff9799fd1b4f8253ee364444f4a2671c3167f143f。

## 阶段 C：属性评价与分析计划冻结

在任何新增属性结果、模型加载或属性视频帧读取之前，以下内容已经冻结：

1. **样本与帧宇宙（研究决定）**：所有 12 个 integrity-PASS 视频、每个原始帧索引 0 至 48；无抽样、无选择性排除、无重生成。
2. **统计单位（研究决定）**：视频是 Pilot 的描述性单位；49 帧只是相关的重复测量，不可伪装成独立样本。
3. **状态/缺失（研究决定）**：仅使用 VALID_OBSERVABLE、UNOBSERVABLE、PIPELINE_FAILURE；后两者永不变成属性缺失或零值。
4. **eyeglasses（研究决定）**：只可使用冻结的 CLIP prompt bank、InsightFace crop 和 margin 规则；不在生成视频上调 prompt、crop 或阈值。
5. **facial hair（研究决定）**：只可使用冻结的 0/1/2/U 盲法人工流程；保留原始 ordinal 标注；单标注者只能作探索性描述。
6. **hair color（研究决定）**：只可使用冻结的 BiSeNet class-17 core ROI 和连续参考相对 L-star；不得新建 light/dark 视频阈值。
7. **Pilot 解释（研究决定）**：分别描述三个属性；不构造总保持率、不做帧级显著性检验、不把 Pilot 异质性升格为 H1-H4 或机制结论。

冻结 artifact：

| Artifact | SHA256 | 作用 |
|---|---|---|
| pilot_v1_1_attribute_evaluation_execution_protocol_v1.md | 432a7f624edc2baacc03b5c7ad6edc6ea0ebf4bf45a9f21366307ca119d77935 | 执行输入、状态、输出和失败规则 |
| pilot_v1_1_analysis_and_claim_plan_v1.md | eab3259fc490250425b6c98e746521b22f6f66b7c2aeaf6eded5165aaa2f6ed4 | 描述性分析与可允许的论文措辞 |
| pilot_attribute_evaluation_output_schema_v1.json | d5075b081648f9d87b584e6478dae745dd0085e1f86b8f49f4e9295afe5fc7f5 | 逐帧和逐视频字段契约 |

## 阶段 D：论文可追溯基础设施

以下表已经建立，但只有 Stage 1 工程完整性行是 verified。任何 pending 行都不能作为论文证据或已核验引用使用。

| 表 | 当前用途 | 关键边界 |
|---|---|---|
| claim_evidence_matrix_v1.csv | 每个主要句子的证据等级与允许措辞 | H1-H4 仍为假说 |
| number_provenance_v1.csv | 每个数字对应 CSV/列、脚本、hash、commit | 49 帧和 588 记录不是独立样本数 |
| figure_table_registry_v1.csv | 每幅图/表的输入、脚本、输出、caption 边界 | contact sheet 仅工程核查 |
| experiment_lineage_v1.csv | manifest 到生成再到 integrity 的 lineage | 属性评价仍为 planned |
| citation_verification_v1.csv | 外部引用的 DOI/URL 与支持句核验 | 网络 gate 未开，所有文献条目均 pending |

## 当前执行 gate 与正确下一步

当前允许的 planning 工作已完成。真正运行 Pilot 属性评价前，必须有一个明确的 operation scope，同时打开：

- G002：为了评价而读取冻结 MP4 的帧；
- G006：离线加载本地 InsightFace、CLIP 和 BiSeNet（并明确 CPU 或 GPU、设备、预算、运行次数和停止规则）；
- G004：若要评价 facial hair，则建立盲法、随机化、匿名 ID、标注者和原始标注保留流程；
- G007：仅当缺少依赖或文献核验需要网络时才单独申请；当前未申请。

## 仍然成立的科学状态

H1、H2、H3、H4 全部仍未检验。reference audit 只说明相应冻结参考图像上指标可用。12/12 generation success 与 Stage 1 integrity PASS 只说明生成链路与文件工程质量；它们均不说明属性保持、身份保持或模型内部因果机制。
