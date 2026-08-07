# 换新卡恢复教程 v2（当前权威版）

本文件取代 `RESTORE_ON_NEW_GPU_CARD_v1.md`；v1 保留为历史记录。恢复的原则是：**先还原并验证，再安装环境或开始任何新计算**。不得在恢复过程中覆盖、重生成、删除或修改 frozen artifact。

## 已有资产

| 资产 | 位置/版本 | 核验 |
|---|---|---|
| 研究代码与轻量证据链 | 私有 GitHub `Yukino00103/finegrained-identity-retention-research` | commit `7a8414fd2c02da789744bd1e4b36844ca570d266` |
| media archive v1 | Windows `E:\Scientific research\Fine-grained character attribute information flow\MP4 image\finegrained_pilot_media_v1.tar.gz` | SHA256 `0be477251d9d25fa35af7cfe1e71882366db37e5ed77f8d68b4ce42ba26405a0` |
| 上游基线 | `PKU-YuanGroup/ConsisID` | commit `60429e4b0d24d36ce8df7fb58f7ab42b86e2b70e` |

media archive v1 已含 12 MP4、12 张 reference 图片、575 个 v2 crops、v2 contact sheets、`private_mapping_v1.csv` 及有关轻量派生产物。它包含人脸和 private mapping，只能私有保存。

## 旧卡释放前的必要补充

media archive v1 **没有**完整包含 `experiments/pilot_v1` 和 `experiments/pilot_v1_1/metric_audit` 中的全部 frozen protocol/spec/readiness/lineage 文件。因此在旧卡释放前，必须在旧卡终端创建并下载补充 archive：

```bash
cd /root/autodl-tmp/finegrained
mkdir -p transfer
tar -czf transfer/finegrained_frozen_context_v2.tar.gz \
  AGENTS.md experiments/pilot_v1 experiments/pilot_v1_1
sha256sum transfer/finegrained_frozen_context_v2.tar.gz \
  > transfer/finegrained_frozen_context_v2.tar.gz.sha256
cat transfer/finegrained_frozen_context_v2.tar.gz.sha256
```

在 Windows 本地 PowerShell 下载它及其 `.sha256`：

```powershell
scp Experiment:/root/autodl-tmp/finegrained/transfer/finegrained_frozen_context_v2.tar.gz "E:\Scientific research\Fine-grained character attribute information flow\MP4 image\finegrained_frozen_context_v2.tar.gz"
scp Experiment:/root/autodl-tmp/finegrained/transfer/finegrained_frozen_context_v2.tar.gz.sha256 "E:\Scientific research\Fine-grained character attribute information flow\MP4 image\finegrained_frozen_context_v2.tar.gz.sha256"
Get-FileHash "E:\Scientific research\Fine-grained character attribute information flow\MP4 image\finegrained_frozen_context_v2.tar.gz" -Algorithm SHA256
```

SHA256 不一致时停止。旧卡未完成此步骤前，不应销毁旧数据盘或声称已拥有完整 frozen-context 备份。

## 新卡恢复步骤

### 1. 克隆研究仓库

在新卡终端执行：

```bash
mkdir -p /root/autodl-tmp/finegrained
cd /root/autodl-tmp/finegrained
git clone https://github.com/Yukino00103/finegrained-identity-retention-research.git research_pipeline
git -C research_pipeline checkout 7a8414fd2c02da789744bd1e4b36844ca570d266
git -C research_pipeline status --short
```

最后一行预期无输出。若私有仓库要求登录，先在新卡完成 `gh auth login`，不要在脚本或 Git 文件中保存 token。

### 2. 从 Windows 上传两个 archive

在 **Windows 本地 PowerShell** 中，`Experiment` 应替换为新卡 SSH alias：

```powershell
ssh Experiment 'mkdir -p /root/autodl-tmp/finegrained/transfer'
scp "E:\Scientific research\Fine-grained character attribute information flow\MP4 image\finegrained_pilot_media_v1.tar.gz" Experiment:/root/autodl-tmp/finegrained/transfer/finegrained_pilot_media_v1.tar.gz
scp "E:\Scientific research\Fine-grained character attribute information flow\MP4 image\finegrained_frozen_context_v2.tar.gz" Experiment:/root/autodl-tmp/finegrained/transfer/finegrained_frozen_context_v2.tar.gz
```

### 3. 在新卡验证 archive 并解压到 staging

```bash
cd /root/autodl-tmp/finegrained
sha256sum transfer/finegrained_pilot_media_v1.tar.gz
# 必须为 0be477251d9d25fa35af7cfe1e71882366db37e5ed77f8d68b4ce42ba26405a0

mkdir -p /root/autodl-tmp/finegrained_restore_stage_v2/media
mkdir -p /root/autodl-tmp/finegrained_restore_stage_v2/context
tar -xzf transfer/finegrained_pilot_media_v1.tar.gz -C /root/autodl-tmp/finegrained_restore_stage_v2/media
tar -xzf transfer/finegrained_frozen_context_v2.tar.gz -C /root/autodl-tmp/finegrained_restore_stage_v2/context

find /root/autodl-tmp/finegrained_restore_stage_v2/media -name '*.mp4' | wc -l
find /root/autodl-tmp/finegrained_restore_stage_v2/media -path '*facial_hair_blinded_materials/crops/*.jpg' | wc -l
test -f /root/autodl-tmp/finegrained_restore_stage_v2/context/AGENTS.md
test -f /root/autodl-tmp/finegrained_restore_stage_v2/context/experiments/pilot_v1/metric_audit/facial_hair_manual_protocol_v2.json
```

预期前两项为 `12` 和 `575`；两个 `test` 命令应成功且没有输出。

### 4. 确认目标为空后恢复 frozen 内容

仅适用于全新工作区。任何目标存在都必须停止并先比较 SHA256，绝不覆盖。

```bash
cd /root/autodl-tmp/finegrained
test ! -e AGENTS.md || { echo 'STOP: AGENTS.md exists'; exit 1; }
test ! -e experiments || { echo 'STOP: experiments exists'; exit 1; }
test ! -e datasets/consisid_eval/extracted/face_images || { echo 'STOP: reference target exists'; exit 1; }
test ! -e research_pipeline/derived/pilot_v1_1/attribute_evaluation_v2/facial_hair_blinded_materials || { echo 'STOP: blinded-material target exists'; exit 1; }

mv /root/autodl-tmp/finegrained_restore_stage_v2/context/AGENTS.md ./AGENTS.md
mv /root/autodl-tmp/finegrained_restore_stage_v2/context/experiments ./experiments
mkdir -p datasets/consisid_eval/extracted
mv /root/autodl-tmp/finegrained_restore_stage_v2/media/datasets/consisid_eval/extracted/face_images datasets/consisid_eval/extracted/face_images
mkdir -p research_pipeline/derived/pilot_v1_1/attribute_evaluation_v2
mv /root/autodl-tmp/finegrained_restore_stage_v2/media/research_pipeline/derived/pilot_v1_1/attribute_evaluation_v2/facial_hair_blinded_materials research_pipeline/derived/pilot_v1_1/attribute_evaluation_v2/facial_hair_blinded_materials
```

archive 中的 annotation/unblinding 轻量文件已经由 Git clone 恢复，不得再用 archive 覆盖 `research_pipeline`。

### 5. 核验关键 frozen artifact

```bash
cd /root/autodl-tmp/finegrained
sha256sum experiments/pilot_v1_1/config.json
sha256sum experiments/pilot_v1_1/manifest.csv
sha256sum experiments/pilot_v1/metric_audit/facial_hair_manual_protocol_v2.json
sha256sum research_pipeline/derived/pilot_v1_1/facial_hair_annotation_round1_v1/annotation_round1_filled_v1.csv
git -C research_pipeline status --short
```

预期 SHA256：

- config：`40014634ef08f17eae3bf41b4d551796efe3855fc7f25c8d3f9b66d9f0e7ef47`
- manifest：`dcf66f0222986403493a7c9a09d310629909d4aef590634348b41ce12544f79d`
- facial-hair manual protocol：`307f2afb4eb92280359960b70eff81cc188d26a60876db896e451f84cc6f25aa`
- frozen annotation CSV：`4f0f9117b9853c4a590e5f5f85eb26154c7cfb64ecb6f3b88b0d91d2684e2824`

### 6. 恢复上游与环境，但不自动运行科研任务

```bash
cd /root/autodl-tmp/finegrained
mkdir -p code
git clone https://github.com/PKU-YuanGroup/ConsisID.git code/ConsisID
git -C code/ConsisID checkout 60429e4b0d24d36ce8df7fb58f7ab42b86e2b70e
git -C code/ConsisID status --short
```

按 `research_pipeline/governance/environment_and_provenance_snapshot_v1.json` 与上游 README 建立新 conda 环境；模型权重/完整数据集应从许可来源重新下载并记录版本、来源和 SHA256。新环境建立不自动授权 GPU、模型加载、视频生成、属性重跑或正式实验。

## 恢复完成条件与当前科研停点

只有 Git commit、两个 archive、关键 frozen SHA256、12 MP4、12 reference 图片、575 v2 crops、v2 contact sheets、private mapping 和 ConsisID commit 均核对成功，才可称为“恢复完成”。

恢复后当前科研停点不变：先完成 fresh reference audit v2 的盲法标注、冻结、揭盲与四项接受规则核验；不得直接执行已冻结但仍 blocked 的 facial-hair 描述性聚合计划。
