# Follow Loop PR lane知识库契约

## 路由

```text
Domains/PR/10-Thinking/PR-Builders/
├── README.md
├── People/<Person>.md
└── PR-Signal-Radar.md

Domains/PR/60-References/Evidence/PR-Builders/
├── People/<Person>-Evidence.md
└── Institutions/<Source>-Evidence.md

Domains/PR/90-System/Follow-Loop/
├── Sources.yml
├── Topics.yml
└── State.md
```

人物档案和趋势雷达属于正在演化的Thinking资产；完整事实、数据、引语和来源核验进入`type: evidence-log`的主体证据日志；来源名单、查询和断点进入System，不进入知识入口。

## 证据归属

- 可明确归因于人物的材料进入该人物唯一Evidence文件。
- 无明确个人归因的机构研究、报告、案例和官方材料进入机构Evidence文件。
- 同一规范化URL只允许存在于一份Evidence记录；人物档案和趋势雷达直接复用。

证据日志Frontmatter固定包含`type: evidence-log`、`status: active`、`domain`、`subject`和`last_reviewed`。

每条证据最低字段：发布主体、发布日期、来源类型、原始链接、核验状态、最近复核日期、支持的判断、边界或疑点、关联信号。人物日志的`subject`承担默认归因；只有来源涉及其他人物或归因存在歧义时，才额外写`可归因人物`。

## 持久化语言边界

人物档案、趋势雷达和Evidence只保存来源事实、长期判断与稳定的证据边界。抓取是否超时、是否使用备用入口、扫描到哪里、断点是否冻结、Harness是否通过、候选数和临时文件位置只进入`State.md`、run manifest或当轮对话。

- 禁止在长期资产使用「本轮」「本次扫描」「此次抓取」「RSS超时」「检查点冻结」等依赖运行现场的措辞。
- 把「本轮未核验」改为「该数字尚未独立核验」；把「本轮只找到一篇」改为「当前档案仅由一项二手来源支撑」；把抓取失败改写为与材料本身有关的核验等级和证据缺口。
- 需要时间边界时使用来源发布日期或`最近复核日期`，不使用收录当下作为叙述参照。

Harness应检查人物、趋势和Evidence中的过程措辞；`State.md`、manifest、Feedback和Test Case不受此语言禁令约束，因为它们承担运行与验证记录。

## 状态与Manifest

`State.md`按`source_id`保存状态。确定性来源使用`scanned_through`；best-effort来源使用`searched_through`。每个来源同时保存最近内容时间、内容ID、最近状态和验证结果。

单次run manifest服从`routing-and-write-contract.md`的统一JSON结构。成功但零新增仍可推进对应扫描水位；失败、部分覆盖和未出现来源保持baseline断点。

## 去重与升级

规范化URL时移除常见追踪参数，保留唯一内容路径或ID。重复来源只补核验、纠错或新归因，不新增重复记录。

单一一手来源可以确认人物此时的表达或组织动作；行业趋势必须按`pr-trend-model.md`满足独立性与证据类型条件。成熟趋势进入现有知识层前先查重，不为目录完整创建空文件。
