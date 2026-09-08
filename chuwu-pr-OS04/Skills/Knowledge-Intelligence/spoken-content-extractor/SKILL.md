---
name: spoken-content-extractor
description: "初五的个人Skill。提取、转录和再利用播客、直播回放、演讲／访谈视频、音频、现成转录或节目文稿。用于生成带时间戳的转录、结构化内容简报、学习指南、亮点、延伸阅读或PR内容资产；普通文章分析、视频剪辑和仅需播放链接的任务不触发本Skill。"
---

# Spoken Content Extractor

> 分享版说明：先读[依赖与使用范围](../../../docs/DEPENDENCIES.md)。本包保留方法与工具，未包含个人知识库、历史案例及运行状态；未附带的知识路径不代表已读取的证据。


> 归属说明：本Skill由初五维护，属于初五的个人Skill体系。分享或再分发时请保留本归属说明及已有来源、作者和许可声明。

## Core Rule

Work only from materials the user can access or has provided. Do not bypass paywalls, private rooms, login-only content, anti-scraping controls, DRM, or platform restrictions. If a link cannot be accessed directly, ask for an exported audio file, copied page text, transcript, show notes, or another accessible source.

## Artifact Placement

Keep execution material and knowledge assets separate from the start:

- **Working layer:** downloaded audio, temporary dependencies, ASR Markdown, JSONL, logs and inspection files go under the current task's `work/`. They are not active knowledge-base content.
- **Source preservation:** only when the user asks to preserve source material for future verification, place original audio and full transcript in the appropriate `Archive/` or `60-References/` location, with provenance and access boundary. Do not place copyrighted full text in an active knowledge entrypoint.
- **Active knowledge layer:** when the user explicitly asks to absorb the episode into the knowledge base, write only evidence-backed facts, short verified quotations, structured Reading or a reusable framework/case. Link to the preserved evidence record; do not copy the full ASR transcript into Domains, README or MOC.
- **No automatic write-back:** extraction, brief and learning-guide requests stay in task outputs unless the user explicitly asks for knowledge-base absorption.

## Mode Gate

Choose the least expensive mode that can support the requested conclusion. Accessible audio is not, by itself, a reason to run full ASR.

1. **Knowledge-increment mode — default for「吸收、归档、看看什么值得入库、提炼长期判断」:**
   - Inspect public metadata, detailed show notes, timeline, linked primary material, and existing knowledge assets first.
   - State the「新增回答的问题」before transcription. If the episode adds no mechanism, evidence, state, boundary, or action, link it as supporting evidence or skip write-back.
   - Use show notes and targeted verification where sufficient. Mark the Evidence `partial` and disclose coverage when part of the episode has not been transcribed or heard.
2. **Targeted-verification mode — default when one or more pivotal claims need audio support:**
   - Use the timeline to transcribe only the relevant windows, normally 2–5 minutes around each target.
   - Verify exact wording against the audio before quoting. Do not upgrade a targeted sample into a whole-episode conclusion.
3. **Full-transcript mode — use only when:**
   - the user explicitly asks for a complete transcript, complete episode summary, or full-coverage study guide;
   - exact quotation coverage across the whole episode is required; or
   - usable show notes/transcripts are absent and the requested conclusion genuinely requires whole-episode coverage.

For multiple episodes, triage every page and test novelty before starting ASR. Do not run two CPU transcription jobs in parallel by default.

## Intake Decision

Identify the available source and proceed with the strongest path:

- Public spoken-content page: inspect HTML/page metadata for accessible audio or video, show notes, title, date, duration, speakers and timeline. On Xiaoyuzhou episode pages, also look for schema.org `associatedMedia.contentUrl` and `og:audio`.
- Audio or video file: choose targeted or full transcription according to the Mode Gate.
- Existing transcript: use it directly; keep original timestamps if present.
- Show notes only: produce a show-note-based brief and clearly say it is not a full transcript.
- Multiple sources: keep source labels and reconcile conflicts conservatively.

Ask for confirmation only when access, copyright, or output purpose is ambiguous.

## Speed Budget

- Abandon a page-loading path after about 30 seconds without useful progress; switch to public HTML, metadata, show notes, or a user-provided file.
- Before a long local ASR run, test a 3–5 minute clip. If projected runtime exceeds 15 minutes per episode or half the audio duration, use targeted verification for knowledge-increment tasks. For an explicitly requested full transcript, report the estimate before continuing.
- Prefer batched decoding with beam size 1 on CPU. Increase beam size or model size only for a named accuracy problem.
- Give the user a progress update at least every 60 seconds during long work. Stop or change strategy when the same path is not producing useful evidence.

## End-to-End Workflow

1. Create a `work/` folder for artifacts when the task is more than a short answer; do not use a Skill directory or an active knowledge directory as scratch space.
2. Preserve provenance: title, podcast/show, host/guest if available, URL/file, duration, date, source type, and access notes.
3. Select a mode and run the novelty test before downloading or transcribing long audio.
4. Extract accessible audio only when the selected mode needs it:
   - Prefer public metadata fields such as `og:audio` or `associatedMedia.contentUrl`.
   - Download only public audio URLs exposed by the page.
   - Keep the original audio in `work/` while processing. Preserve it beyond the task only under the source-preservation rule above.
5. Transcribe audio:
   - Prefer `scripts/transcribe_audio.py` for local timestamped transcript generation.
   - If local transcription dependencies are unavailable, install them under the current task's `work/` folder or ask the user for permission/alternative only when needed.
   - For targeted verification, record every processed time window and do not label the result「完整逐字稿」.
   - For full transcription, produce both Markdown and JSONL when possible.
6. Verify coverage:
   - For full transcription, check audio duration against the final transcript timestamp, plus file size, segment count, beginning, and tail.
   - For targeted transcription, verify only the declared windows and retain a `partial` evidence boundary.
   - Note that automatic transcripts can misrecognize names and technical terms.
7. Index long full transcripts before analysis:
   - Run`scripts/index_transcript.py build`on the timestamped JSONL, then run`verify`; keep the index and chunks in the task's`work/`folder.
   - For the first comprehensive output, process every indexed chunk exactly once in order and write a compact evidence map with chunk ID, time range, speakers, themes, claims, facts, quote candidates, and uncertainties. Build the final answer from that map; reopen source chunks only for exact quotations or fact checks.
   - For follow-up questions or new repurposing, search the index and evidence map first. A change of audience, language or output format reuses the complete evidence map. If a new whole-episode question needs a dimension absent from that map, review all chunks for that missing dimension; do not treat partial keyword matches as proof that a theme is absent. Preserve source hashes and coverage so unchanged evidence is not reread without a reason.
8. Extract and study:
   - Build a structured brief from the transcript.
   - Highlight key passages with timestamps.
   - Explain concepts, frameworks, and assumptions.
   - Convert ideas into practical questions and reusable checklists.
   - Add credible reference readings when the user asks to learn or apply the content.
9. Repurpose only after extraction: create PR notes, social posts, newsletter copy, internal briefings, or learning materials from transcript-grounded content, not guesses.
10. Before any knowledge-base write-back, classify each artifact using the Artifact Placement rule. Full transcript and JSONL never become an active knowledge entrypoint.

## Local Transcription Script

Use `scripts/transcribe_audio.py` for long audio when a local transcript is needed.

Example:

```bash
python3 -m pip install --target work/.deps-fw faster-whisper
PYTHONPATH=work/.deps-fw python3 /path/to/skill/scripts/transcribe_audio.py \
  --audio episode.m4a \
  --title "节目标题" \
  --source-url "https://www.xiaoyuzhoufm.com/episode/..." \
  --model small \
  --language zh \
  --beam-size 1 \
  --batch-size 8 \
  --out-prefix episode-transcript \
  --prompt "中文商业播客，涉及品牌、营销、AI、CLV、ROI。"
```

For targeted verification, bound the requested window:

```bash
PYTHONPATH=work/.deps-fw python3 /path/to/skill/scripts/transcribe_audio.py \
  --audio episode.m4a \
  --clip-start 1140 \
  --clip-end 1440 \
  --out-prefix episode-19m-to-24m
```

Prefer `small`, CPU `int8`, beam size 1, and batched decoding for speed. Use `medium` or a larger beam only for a named accuracy problem. For long Chinese podcasts, include a domain prompt with likely names, terms, and English acronyms.

## Transcript Index

The index reduces repeated transcript loading; it never replaces the full transcript. Build and verify it after JSONL transcription:

```bash
python3 /path/to/skill/scripts/index_transcript.py build \
  --jsonl work/episode-transcript.jsonl \
  --out-dir work/episode-index \
  --chunk-seconds 300
python3 /path/to/skill/scripts/index_transcript.py verify \
  --index work/episode-index/index.json
```

For a follow-up, retrieve a small candidate set before opening source chunks:

```bash
python3 /path/to/skill/scripts/index_transcript.py search \
  --index work/episode-index/index.json \
  --query "创始人叙事 信任" \
  --limit 6
```

`verify`must confirm the source SHA-256 and reproduce every source segment in order. Keep`index.json`, chunk Markdown/JSONL and the evidence map in`work/`; they are execution artifacts, not active knowledge entries. Lexical search is a retrieval aid, not evidence of absence. For conceptual questions, derive several transcript terms from the evidence map and search again. Exact quotations must be checked against the returned timestamped source chunk.

## Output Defaults

For extraction/summarization:

```markdown
## 基本信息
## 一句话结论
## 核心摘要
## 主题脉络
## 关键观点
## 可引用表达
## 适合二次传播的素材
## 风险与待核实点
```

For learning/study requests, read `references/study-guide-patterns.md` and produce a study guide with:

- top-level learning conclusion
- what to learn
- timestamped highlights
- concept explanations
- knowledge map
- application questions
- reference readings
- second-listen plan

Use Chinese by default for Chinese-language podcast content.

## Quality Bar

- Separate verbatim transcript lines from paraphrased highlights.
- Keep timestamps whenever the transcript has them.
- Flag uncertain automatic transcription terms as "待核实".
- Label show-note-only and targeted-transcription Evidence as `partial`; state exactly which ranges or claims were checked.
- Do not invent sources or references; if browsing, prefer primary/credible sources.
- When quoting from transcript/audio, keep quotes short and grounded in the generated transcript.
- For learning guides, focus on transfer: how the user can use the knowledge in work, judgment, writing, strategy, or personal growth.
- Before writing to the knowledge base, confirm that the output is a durable Evidence, Reading, case or framework rather than a transcript, run note or temporary file.

## References

- Read `references/output-patterns.md` for content briefs, PR/media notes, and social repurposing.
- Read `references/study-guide-patterns.md` for learning guides, highlights, reference lists, and knowledge-application outputs.
