# 依赖与使用范围

## 路径约定

Skills/下保持原分类目录。相对references、assets、scripts路径从对应Skill目录解析；Domains/和Skills/registry.yml从本合集根目录解析。已附带的共享方法位于Domains/PR/35-Frameworks和45-Workflows。

原个人知识库中的其他Domains路径属于外部依赖：[路径清单](external-knowledge-paths.json)。未附带的理论、案例、Evidence与扩展Workflow不得伪称已读取、已核验，也不自动去初五的电脑路径寻找。使用现有Skill正文和用户材料可以完成的部分继续；缺失内容会实质影响任务时明确缺口或由使用者提供相应资料。

只复制单个Skill目录可能丢失共享方法。保留整个合集，或在安装时同时提供上述共享目录并明确合集根目录；本包未验证每一种Agent工具的自动安装行为。

## 全年公关战略与PR交接

全年公关战略的三份Workflow已随包附带，按Skill选择媒体关系、舆情管理或综合模式。共享的PR交接协议、决策门和输出质量框架也已附带。企业经营、预算、联系人、KPI和历史事件仍须由使用者提供。

其他知识地图保留来源线索。没有已附带的理论全文与历史案例时，以当前材料形成有边界判断，不引用未读到的知识条目作证据。

## Follow Loop接入条件

本包提供方法与原有脚本，未提供一套可以直接抓取运行的个人知识库。首次接入必须具备：

- 使用者自己的知识库根目录与适用AGENTS.md。
- Domains/PR/45-Workflows/Workflow_Follow-Loop.md及其完整任务合同。
- Domains/PR/90-System/Follow-Loop/下的Config.yml、Topics.yml、Sources.yml、State.md、Case-State.yml；来源、断点及开放复核均由使用者自建。
- 五条lane所需的Evidence、人物／组织档案、信号雷达、索引和运行目录；结构见Skill参考合同。
- 知识库本身的.codex/checks/kb_check.rb及其依赖。
- Python3.10或更新版本、Ruby及其YAML标准库，以及完成来源访问与事实核验所需的工具。

完整运行时，将本Skill按Skills/Knowledge-Intelligence/follow-loop/结构放进使用者知识库。Ruby查询工具从该结构定位根目录，Python Harness的--root必须指向同一根目录。示例中的PR_KNOWLEDGE_ROOT由使用者设置，不预置初五的电脑路径。

缺少上述依赖时停止Loop启动，列出接入缺口；不能生成假来源、假断点或空配置来宣称验收通过。普通公关与研究Skill的独立任务不因此被阻塞。本次未执行Follow Loop在线采集和知识写回。

## 口述内容处理

已有完整转录可直接用于分析。原始视频或音频需要宿主可用的转录工具；附带transcribe_audio.py使用faster-whisper，首次调用可能下载模型，依赖和模型由使用者自行配置。index_transcript.py用于本地转录索引。分享包未携带音视频、转录正文、模型权重或访问凭据。

## 其他脚本

现有Python工具建议在Python3.10或更新版本运行。未特别声明的脚本使用标准库；实际转录的faster-whisper属于额外依赖。打包检查不代表执行过所有业务功能、网络来源或音频转录。
