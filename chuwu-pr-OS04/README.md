# Chuwu PR OS04｜初五的公关与研究Skill合集

当前版本：OS04。

由初五维护的13个个人Skill，覆盖年度公关战略、文案审查、舆情判断、消费者与行业研究，以及情报和口述内容处理。

面向实际工作：从用户提供的材料与问题出发，区分事实、解释与假设，交付有依据的判断、方案或文件。资料缺失时保留边界，不虚构企业事实与研究结果。

## Skill清单

| 类别 | Skill | 调用名 |
| --- | --- | --- |
| 公关 | [全年公关战略](Skills/PR/annual-pr-strategy/SKILL.md) | `annual-pr-strategy` |
| 公关 | [文案公共语境审查](Skills/PR/copy-lens-review/SKILL.md) | `copy-lens-review` |
| 公关 | [热点舆情分析](Skills/PR/hot-public-opinion-analysis/SKILL.md) | `hot-public-opinion-analysis` |
| 公关 | [判断中枢](Skills/PR/judgment-hub/SKILL.md) | `judgment-hub` |
| 公关 | [稿件叙事分析](Skills/PR/media-narrative-analysis/SKILL.md) | `media-narrative-analysis` |
| 公关 | [消费者研究的PR转换](Skills/PR/pr-consumer-research/SKILL.md) | `pr-consumer-research` |
| 公关 | [公关预案](Skills/PR/pr-contingency-plan/SKILL.md) | `pr-contingency-plan` |
| 公关 | [新闻通稿](Skills/PR/press-release/SKILL.md) | `press-release` |
| 研究 | [消费者研究](Skills/Research/consumer-research/SKILL.md) | `consumer-research` |
| 研究 | [行业媒体研究](Skills/Research/industry-media-research/SKILL.md) | `industry-media-research` |
| 研究 | [行业研究](Skills/Research/industry-research/SKILL.md) | `industry-research` |
| 知识与情报 | [情报增量闭环](Skills/Knowledge-Intelligence/follow-loop/SKILL.md) | `follow-loop` |
| 知识与情报 | [口述内容提取](Skills/Knowledge-Intelligence/spoken-content-extractor/SKILL.md) | `spoken-content-extractor` |

## 开始使用

1. 先读[依赖与使用范围](docs/DEPENDENCIES.md)，再按当前任务选择一个主Skill。
2. 在支持SKILL.md的Agent工具中加载对应目录，或让Agent读取对应的SKILL.md并执行。不要一次加载全部13项。
3. 保留完整仓库的目录结构。只复制一份SKILL.md会丢失references、模板、脚本和共享方法；使用工具的安装功能时也要核对共享依赖是否随包保留。
4. 提供真实材料、要解决的问题与必要约束。例如：「使用press-release，根据以下事实写新品通稿；未确认的性能保留待补项。」

本合集没有自动安装、联网、定时任务或批量写回入口。普通分析和文稿可按已提供材料执行；转录需音频及相应工具；Follow Loop的完整增量运行需使用者另行配置兼容知识库。

## 本包包含什么

- 13个Skill的运行说明、参考文件、模板及现有脚本。
- 全年公关战略的3份Workflow、PR交接协议、决策门与输出质量框架，共6份共享方法文件。
- 初五归属说明、打包清单、文件校验信息及GitHub Desktop上传说明。

本包未附带完整PR Knowledge OS、私人原始材料、历史案例与Feedback记录、来源账号池、扫描断点、运行清单或本机配置。Follow Loop只提取保留当前采样规则，不导出个人选择历史。知识地图中的未附带条目已标明为外部知识依赖，不能当作已读取的依据。

## 验证状态

这是2026-09-08制作的分享副本。13项均处于experimental阶段；源知识库登记的11项有真实任务记录，annual-pr-strategy与industry-media-research为静态验证。历史任务记录未放入分享包；这些标签不代表分享版已在其他人的环境中通过真实业务测试。

本次打包检查和实际范围见[打包检查报告](docs/PACKAGE-CHECK.md)。

## 归属与分享

本合集由初五整理和维护。分享或再分发时保留初五署名、已有来源、作者和许可声明；第三方理论、方法或工具的引用不应被解读为全部由初五原创。详见[归属说明](COPYRIGHT.md)。

本次没有指定统一开源许可证，也没有添加MIT等授权。上传到GitHub与选择开源授权是两个独立决定。

## 版本与获取

OS04覆盖公关8项、研究3项、知识与情报2项，共13个Skill。相对OS03的6项公关Skill，本版增加年度公关战略、消费者研究的PR转换、消费者研究、行业媒体研究、行业研究、Follow Loop与口述内容提取。

OS03的历史内容保留在Git提交记录中。完整下载可在仓库使用Code → Download ZIP；使用GitHub Desktop时克隆现有仓库，后续通过Fetch／Pull获取更新。详见[GitHub Desktop使用说明](docs/GITHUB-DESKTOP.md)。

仓库：[chuwu57/Chuwu-PR-OS](https://github.com/chuwu57/Chuwu-PR-OS)。
