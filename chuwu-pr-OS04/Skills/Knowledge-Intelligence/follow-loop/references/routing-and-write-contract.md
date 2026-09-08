# Follow Loop路由与写入契约

## 统一状态

- 来源、主题、断点：`Domains/PR/90-System/Follow-Loop/`。
- Case Follow去重与开放复核：`Domains/PR/90-System/Follow-Loop/Case-State.yml`。
- 运行现场只进入只读baseline、90-System/Follow-Loop/Runs中的恢复manifest和当轮对话，不进入知识正文。

## 结果路由

| route | Evidence | 长期资产 | 写入门禁 |
|---|---|---|---|
| `ai_person` | `Domains/PR/60-References/Evidence/AI-Builders/<Person>-Evidence.md` | `Domains/AI/Builders/<Person>.md` | 原始来源核验后可写；外部普遍命题仍需独立复核 |
| `pr_person` | `Domains/PR/60-References/Evidence/PR-Builders/People/<Person>-Evidence.md` | `Domains/PR/10-Thinking/PR-Builders/People/<Person>.md` | 必须可明确归因；机构无署名内容不得写入 |
| `pr_signal` | PR人物或机构Evidence | `Domains/PR/10-Thinking/PR-Builders/PR-Signal-Radar.md` | 阶段升级必须满足趋势模型 |
| `case_candidate` | `Domains/PR/60-References/Evidence/`中的现有或新Evidence | `Case-State.yml`；成熟后进入Case、Principle、Framework、Strategy或Workflow | 候选只进状态；知识写入必须先给精确路径并获得用户确认 |
| `embodied_entity` | `Domains/PR/60-References/Evidence/Embodied-Intelligence/<Entity>-Evidence.md` | `Domains/AI/Embodied-Intelligence/Entities/<Entity>.md` | 必须改变对象路线或证据边界；融资和单次Demo不足 |
| `embodied_signal` | 具身智能对象Evidence | `Domains/AI/Embodied-Intelligence/Embodied-Intelligence-Signal-Radar.md` | 至少两个独立主体、两类证据并保留反证 |
| `luxury_entity` | `Domains/PR/60-References/Evidence/Luxury/<Entity>-Evidence.md` | `Domains/Business/Luxury/Entities/<Entity>.md` | 必须改变对象的品牌、渠道、组织或经营坐标 |
| `luxury_signal` | 奢侈品对象或市场Evidence | `Domains/Business/Luxury/Luxury-Intelligence-Radar.md` | 至少两个独立对象、两类来源并有经营或消费者结果 |

## 一源多路由

1.以规范化URL作为来源唯一键，移除常见追踪参数。
2.同一材料只获取和核验一次。
3.可归因人物、组织动作和行业信号可以分别形成证据单元，但不得复制相同来源事实。
4.已有Evidence能够承担新路由时直接复用；只有现有记录无法表达新的归因主体时才补充对应人物Evidence。
5.人物更新记录继续直接链接原文；Frontmatter的`evidence`负责连接内部证据记录。

## Case Follow知识门禁

- 候选和复核状态只保存在`90-System/Follow-Loop`，不创建日期化Markdown报告。
- 用户说「保留：编号」后完成事实核验与方法研究，并在对话中给出结论。
- 研究成熟时必须列出拟新增或修改的具体知识路径、Evidence、支持或挑战的判断以及仍不足的事实。
- 用户确认后才写入知识层。达到案例库门禁的危机案例进入`20-PR-Case-Library`；方法判断进入已有Thinking、Principle、Framework、Strategy或Workflow，先查重再补充。
- 研究不足时只更新`Case-State.yml`的开放问题，不创建半成品知识卡。

## 状态与幂等恢复

- 每个来源拥有独立断点，禁止使用全局时间替代。
- 成功且零新增可以推进扫描水位。
- `failed`、部分覆盖和未出现在manifest中的来源保持baseline断点。
- 资产预检后最后写入State，再对写入后的State执行baseline＋manifest检查；失败则冻结／恢复受影响水位。这里的「最后」指writes内的知识资产与运行状态，manifest自身的审计更新不列入writes。

统一JSON manifest最低结构：

```json
{
  "requested_from": "2026-07-26T00:00:00Z",
  "requested_through": "2026-07-28T00:00:00Z",
  "selected_source_ids": ["ai-builder-x-feed"],
  "sources": [
    {
      "source_id": "ai-builder-x-feed",
      "lane": "ai_follow",
      "coverage_mode": "deterministic",
      "status": "success",
      "covered_from": "2026-07-26T00:00:00Z",
      "covered_through": "2026-07-28T00:00:00Z",
      "candidates_seen": 12,
      "valid_items": 2,
      "next_checkpoint": "2026-07-28T00:00:00Z"
    }
  ],
  "writes": [
    "Domains/PR/60-References/Evidence/AI-Builders/<Person>-Evidence.md",
    "Domains/AI/Builders/<Person>.md",
    "Domains/PR/90-System/Follow-Loop/State.md"
  ]
}
```

- `selected_source_ids`为本轮活跃来源子集，省略时表示全部；`sources`必须完整覆盖所选来源且按`source_id`唯一；`lane`只使用`ai_follow`、`pr_follow`、`case_follow`、`embodied_follow`或`luxury_follow`。
- 候选结果使用路由枚举；同一材料需要跨线复用时在来源对象的`routes`数组记录，但来源事实只核验和保存一次。
- `success`必须填写实际覆盖、候选数、有效数和`next_checkpoint`；`failed`或`partial`必须填写`error`，且断点不变。
- `writes`按实际保存顺序记录，并只能列已存在的库内文件；该清单不能证明历史执行顺序或全事务原子性。没有长期资产写入时仍把最后推进的State列为最后一项；状态不变时不列State。

同一候选、拟写路径与内容在当前任务已获明确批准时，复用该授权；只在范围、路径或主张发生实质变化时再确认。候选选择与正式入库是不同动作；等待只阻断该候选的入库步骤。
