# 换新卡恢复教程 v1

## 目的与恢复边界

本教程用于在新的 AutoDL/GPU 实例上恢复本项目的代码、治理记录、冻结输入和已完成的 Pilot 证据链。先恢复并核验，再决定是否安装依赖、下载模型/数据集或开始任何新科研阶段。

本教程不会授权重新生成视频、改写 frozen artifact、改变阈值/标签/样本、直接运行 formal experiment，或绕过现有 Human Gate。

## 当前恢复资产清单

### 已在私有 GitHub 保存的轻量资产

- 研究仓库：`https://github.com/Yukino00103/finegrained-identity-retention-research.git`
- 当前恢复基线 commit：`7a8414fd2c02da789744bd1e4b36844ca570d266`
- 内容：研究代码、治理文件、协议副本/引用、schema、CSV/JSON、SHA256、日志、小型图、artifact registry、lineage、claim–evidence、论文草稿与研究记录。

### 已下载到 Windows 本地的 media archive v1

- Windows 位置：`E:\Scientific research\Fine-grained character attribute information flow\MP4 image\finegrained_pilot_media_v1.tar.gz`
- SHA256：`0be477251d9d25fa35af7cfe1e71882366db37e5ed77f8d68b4ce42ba26405a0`
- 已包含：12 个 MP4、12 张冻结 reference 图片、575 张 v2 facial-hair crops、v2 contact sheets、`private_mapping_v1.csv`、manifest/config/generation summary，以及相关的冻结标注/揭盲派生产物。
- 不要公开分享该 archive：其中包含人脸图像和 private mapping。

### 重要：media archive v1 不是完整 frozen-context snapshot

它**不包含** `experiments/pilot_v1/metric_audit/facial_hair_manual_protocol_v2.json`、`experiments/pilot_v1_1/metric_audit/video_evaluation_protocol_v1.json` 等实验目录中的全部 frozen 上游材料。因此，在释放旧卡或删除旧数据盘前，必须完成本文第 0 步的补充备份。没有该补充备份时，不应声称新卡恢复了完整科研证据链。

### 可重新下载，但必须版本固定的材料

- 上游 ConsisID：`https://github.com/PKU-YuanGroup/ConsisID.git`，固定 commit `60429e4b0d24d36ce8df7fb58f7ab42b86e2b70e`。
- 模型权重和完整数据集：新卡可重新下载，但只能使用明确记录的来源、版本/commit、许可与 SHA256。不得把下载到的“最新版”静默当成本次 Pilot 的输入。
- 环境目标参见 `governance/environment_and_provenance_snapshot_v1.json`：Python 3.11.15、PyTorch 2.5.1+cu121、diffusers 0.33.1、transformers 4.46.3 等。新环境必须另行记录新快照，不能假装与旧环境字节相同。

## 第 0 步：旧卡释放前必须补做 frozen-context archive

在**当前旧卡**的远程终端执行。该操作只读取现有 artifact，生成新 archive；不修改任何 frozen 输入。

```bash
cd /root/autodl-tmp/finegrained
mkdir -p transfer

tar -czf transfer/finegrained_frozen_context_v2.tar.gz \
  AGENTS.md \
  experiments/pilot_v1 \
  experiments/pilot_v1_1

sha256sum transfer/finegrained_frozen_context_v2.tar.gz \
  > transfer/finegrained_frozen_context_v2.tar.gz.sha256

ls -lh transfer/finegrained_frozen_context_v2.tar.gz
cat transfer/finegrained_frozen_context_v2.tar.gz.sha256
```

把该 `.tar.gz` 和 `.sha256` 下载到与 media archive 相同的 Windows 文件夹。Windows PowerShell 中，先确保目录存在，再使用**完整目标文件名**（不要以反斜杠结尾）：

```powershell
New-Item -ItemType Directory -Force -Path 'E:\Scientific research\Fine-grained character attribute information flow\MP4 image'

scp Experiment:/root/autodl-tmp/finegrained/transfer/finegrained_frozen_context_v2.tar.gz "E:\Scientific research\Fine-grained character attribute information flow\MP4 image\finegrained_frozen_context_v2.tar.gz"

scp Experiment:/root/autodl-tmp/finegrained/transfer/finegrained_frozen_context_v2.tar.gz.sha256 "E:\Scientific research\Fine-grained character attribute information flow\MP4 image\finegrained_frozen_context_v2.tar.gz.sha256"
```

下载后在 Windows 验证 SHA256；只有与 `.sha256` 文件完全一致才可释放旧卡：

```powershell
Get-FileHash "E:\Scientific research\Fine-grained character attribute information flow\MP4 image\finegrained_frozen_context_v2.tar.gz" -Algorithm SHA256
```

## 第 1 步：在新卡建立空工作区并恢复 GitHub 研究仓库

在新卡远程终端执行。以下使用原有工作区路径，以便 CSV 内记录的绝对路径仍然成立。

```bash
mkdir -p /root/autodl-tmp/finegrained
cd /root/autodl-tmp/finegrained

git clone https://github.com/Yukino00103/finegrained-identity-retention-research.git research_pipeline
git -C research_pipeline checkout 7a8414fd2c02da789744bd1e4b36844ca570d266
git -C research_pipeline status --short
```

预期：最后一条命令没有输出。若 private repository 要求认证，先在新卡运行 `gh auth login`，然后重新 clone；不要把 token 写进脚本或 Git 文件。

核对基线：

```bash
git -C /root/autodl-tmp/finegrained/research_pipeline rev-parse HEAD
sha256sum /root/autodl-tmp/finegrained/research_pipeline/governance/artifact_registry_v5.csv
```

预期 commit 为 `7a8414fd2c02da789744bd1e4b36844ca570d266`；`artifact_registry_v5.csv` SHA256 为 `4b2ef29bf8a2d7706fad4345dc11b07788a4b7d131fa4830c968819aaa97c5e9`。

## 第 2 步：从 Windows 上传两个 archive 到新卡

先在**Windows 本地 PowerShell**中，把 `Experiment` 替换为新卡对应的 SSH alias（若新卡仍使用该 alias，可直接保留）。

```powershell
ssh Experiment 'mkdir -p /root/autodl-tmp/finegrained/transfer'

scp "E:\Scientific research\Fine-grained character attribute information flow\MP4 image\finegrained_pilot_media_v1.tar.gz" Experiment:/root/autodl-tmp/finegrained/transfer/finegrained_pilot_media_v1.tar.gz

scp "E:\Scientific research\Fine-grained character attribute information flow\MP4 image\finegrained_frozen_context_v2.tar.gz" Experiment:/root/autodl-tmp/finegrained/transfer/finegrained_frozen_context_v2.tar.gz
```

建议也上传两个 `.sha256` 文件，以保留原始备份证据。

## 第 3 步：在新卡先验证 archive，再解压到 staging

在新卡远程终端执行。哈希不符时立即停止，不解压、不重试覆盖。

```bash
cd /root/autodl-tmp/finegrained

sha256sum transfer/finegrained_pilot_media_v1.tar.gz
# 必须为：0be477251d9d25fa35af7cfe1e71882366db37e5ed77f8d68b4ce42ba26405a0

mkdir -p /root/autodl-tmp/finegrained_restore_stage_v1/media
mkdir -p /root/autodl-tmp/finegrained_restore_stage_v1/context

tar -xzf transfer/finegrained_pilot_media_v1.tar.gz -C /root/autodl-tmp/finegrained_restore_stage_v1/media
tar -xzf transfer/finegrained_frozen_context_v2.tar.gz -C /root/autodl-tmp/finegrained_restore_stage_v1/context
```

先检查 staging 内容；此时不要覆盖工作区：

```bash
find /root/autodl-tmp/finegrained_restore_stage_v1/media -name '*.mp4' | wc -l
find /root/autodl-tmp/finegrained_restore_stage_v1/media -path '*facial_hair_blinded_materials/crops/*.jpg' | wc -l
test -f /root/autodl-tmp/finegrained_restore_stage_v1/context/experiments/pilot_v1/metric_audit/facial_hair_manual_protocol_v2.json
test -f /root/autodl-tmp/finegrained_restore_stage_v1/context/experiments/pilot_v1_1/metric_audit/video_evaluation_protocol_v1.json
```

预期分别为 `12`、`575`，两个 `test` 命令均无输出且退出成功。

## 第 4 步：在确认目标路径为空后恢复 frozen 实验材料

这一步只适用于全新工作区。若目标已存在，停止并比较 SHA256，不要覆盖。

```bash
cd /root/autodl-tmp/finegrained

test ! -e experiments || { echo 'STOP: experiments already exists'; exit 1; }
test ! -e datasets/consisid_eval/extracted/face_images || { echo 'STOP: reference-image target already exists'; exit 1; }
test ! -e research_pipeline/derived/pilot_v1_1/attribute_evaluation_v2/facial_hair_blinded_materials || { echo 'STOP: blinded-material target already exists'; exit 1; }

mv /root/autodl-tmp/finegrained_restore_stage_v1/context/experiments ./experiments
mkdir -p datasets/consisid_eval/extracted
mv /root/autodl-tmp/finegrained_restore_stage_v1/media/datasets/consisid_eval/extracted/face_images datasets/consisid_eval/extracted/face_images
mkdir -p research_pipeline/derived/pilot_v1_1/attribute_evaluation_v2
mv /root/autodl-tmp/finegrained_restore_stage_v1/media/research_pipeline/derived/pilot_v1_1/attribute_evaluation_v2/facial_hair_blinded_materials research_pipeline/derived/pilot_v1_1/attribute_evaluation_v2/facial_hair_blinded_materials
```

media archive 中另有 GitHub 已保存的轻量 annotation/unblinding 文件；不要用 archive 覆盖 clone 下来的 `research_pipeline` 文件。Git 的版本才是该类轻量 artifact 的恢复来源。

## 第 5 步：核验关键 frozen artifact

```bash
cd /root/autodl-tmp/finegrained

sha256sum experiments/pilot_v1_1/config.json
sha256sum experiments/pilot_v1_1/manifest.csv
sha256sum experiments/pilot_v1/metric_audit/facial_hair_manual_protocol_v2.json
sha256sum research_pipeline/derived/pilot_v1_1/facial_hair_annotation_round1_v1/annotation_round1_filled_v1.csv

git -C research_pipeline status --short
```

预期关键 SHA256：

- config：`40014634ef08f17eae3bf41b4d551796efe3855fc7f25c8d3f9b66d9f0e7ef47`
- manifest：`dcf66f0222986403493a7c9a09d310629909d4aef590634348b41ce12544f79d`
- facial-hair manual protocol：`307f2afb4eb92280359960b70eff81cc188d26a60876db896e451f84cc6f25aa`
- frozen annotation CSV：`4f0f9117b9853c4a590e5f5f85eb26154c7cfb64ecb6f3b88b0d91d2684e2824`

任何 SHA256 不符、文件缺失、Git 工作树意外变化或 schema 错误都应停止，并回到备份源核查；不要下载替代文件或覆盖 frozen artifact 来“修复”。

## 第 6 步：恢复上游代码和环境（不自动开始实验）

```bash
cd /root/autodl-tmp/finegrained
mkdir -p code
git clone https://github.com/PKU-YuanGroup/ConsisID.git code/ConsisID
git -C code/ConsisID checkout 60429e4b0d24d36ce8df7fb58f7ab42b86e2b70e
git -C code/ConsisID status --short
```

上游目录必须保持只读基线；新研究代码只写入 `research_pipeline`。随后按上游 README 和环境快照建立新的 conda 环境、下载经过许可核验的模型权重/数据集，并记录新环境与模型 SHA256。该软件恢复不自动授权 GPU、模型加载、视频生成、属性重跑或正式实验。

## 恢复完成判定

只有同时满足以下条件，才可称为“恢复完成、等待下一科研授权”：

1. GitHub research commit 与 `7a8414f...` 一致且工作树干净；
2. 两个 archive SHA256 均匹配；
3. 12 个 MP4、12 张 reference 图片、575 个 v2 crops、v2 contact sheets 与 private mapping 存在；
4. config、manifest、frozen manual protocol、frozen annotation CSV 的 SHA256 均匹配；
5. ConsisID 位于固定 commit `60429e4...` 且工作树干净；
6. 新环境、模型权重和数据集来源/版本/哈希另行记录；
7. 恢复过程中没有覆盖、重生成、选择性删除或重新标注任何 frozen artifact。

恢复完成后，当前下一科研门仍是：fresh reference audit v2 的盲法标注、冻结、揭盲与四项接受规则核验。不得直接执行已冻结但仍 blocked 的 facial-hair 聚合计划。
