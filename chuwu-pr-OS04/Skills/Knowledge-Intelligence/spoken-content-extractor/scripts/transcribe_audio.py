#!/usr/bin/env python3
"""Transcribe local audio with faster-whisper into timestamped Markdown and JSONL."""

import argparse
import json
from pathlib import Path


def timestamp(seconds: float) -> str:
    seconds = max(0, float(seconds))
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Transcribe audio into Markdown and JSONL.")
    parser.add_argument("--audio", required=True, help="Local audio file path.")
    parser.add_argument("--out-prefix", default=None, help="Output prefix without extension.")
    parser.add_argument("--title", default="音频逐字转写", help="Transcript title.")
    parser.add_argument("--source-url", default="", help="Original source URL.")
    parser.add_argument("--model", default="small", help="faster-whisper model size or path.")
    parser.add_argument("--language", default="zh", help="Language code, e.g. zh or en.")
    parser.add_argument("--prompt", default="", help="Initial prompt with domain terms.")
    parser.add_argument("--download-root", default=".hf-models", help="Model download/cache folder.")
    parser.add_argument("--compute-type", default="int8", help="CTranslate2 compute type.")
    parser.add_argument("--beam-size", type=int, default=1, help="Decoding beam size; 1 is fastest.")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=8,
        help="Batched decoding size; use 0 for the standard pipeline.",
    )
    parser.add_argument("--clip-start", type=float, default=None, help="Start second for targeted ASR.")
    parser.add_argument("--clip-end", type=float, default=None, help="End second for targeted ASR.")
    parser.add_argument("--no-vad", action="store_true", help="Disable VAD filter.")
    return parser.parse_args()


def clip_ranges(start: float, end: float) -> list[dict[str, float]]:
    """Split a targeted window into 30-second ranges for batched inference."""
    ranges = []
    cursor = start
    while cursor < end:
        next_end = min(cursor + 30.0, end)
        ranges.append({"start": cursor, "end": next_end})
        cursor = next_end
    return ranges


def main() -> None:
    args = parse_args()
    audio = Path(args.audio)
    if not audio.exists():
        raise FileNotFoundError(audio)

    clipped = args.clip_start is not None or args.clip_end is not None
    if clipped:
        if args.clip_start is None or args.clip_end is None:
            raise SystemExit("Use --clip-start and --clip-end together.")
        if args.clip_start < 0 or args.clip_end <= args.clip_start:
            raise SystemExit("Targeted clip must satisfy 0 <= clip-start < clip-end.")

    try:
        from faster_whisper import BatchedInferencePipeline, WhisperModel
    except ImportError as exc:
        raise SystemExit(
            "Missing faster-whisper. Install locally with: "
            "python3 -m pip install --target .deps-fw faster-whisper; "
            "then run with PYTHONPATH=.deps-fw"
        ) from exc

    out_prefix = args.out_prefix or audio.with_suffix("").name + "-transcript"
    md_path = Path(out_prefix + ".md")
    jsonl_path = Path(out_prefix + ".jsonl")

    print(f"Loading model: {args.model}", flush=True)
    model = WhisperModel(
        args.model,
        device="cpu",
        compute_type=args.compute_type,
        download_root=args.download_root,
    )

    common_options = {
        "language": args.language,
        "task": "transcribe",
        "beam_size": args.beam_size,
        "best_of": 1,
        "temperature": 0,
        "initial_prompt": args.prompt or None,
        "condition_on_previous_text": True,
        "log_progress": True,
    }

    use_batch = args.batch_size > 0 and (not args.no_vad or clipped)
    if use_batch:
        pipeline = BatchedInferencePipeline(model=model)
        batch_clips = clip_ranges(args.clip_start, args.clip_end) if clipped else None
        mode = f"batched targeted {timestamp(args.clip_start)}-{timestamp(args.clip_end)}" if clipped else "batched full"
        print(f"Transcribing: {mode} batch_size={args.batch_size} beam_size={args.beam_size}", flush=True)
        segments, _info = pipeline.transcribe(
            str(audio),
            vad_filter=not args.no_vad and not clipped,
            clip_timestamps=batch_clips,
            batch_size=args.batch_size,
            **common_options,
        )
    else:
        standard_clips = [args.clip_start, args.clip_end] if clipped else "0"
        mode = f"standard targeted {timestamp(args.clip_start)}-{timestamp(args.clip_end)}" if clipped else "standard full"
        print(f"Transcribing: {mode} beam_size={args.beam_size}", flush=True)
        segments, _info = model.transcribe(
            str(audio),
            vad_filter=not args.no_vad,
            clip_timestamps=standard_clips,
            **common_options,
        )

    count = 0
    last_end = 0.0
    with md_path.open("w", encoding="utf-8") as md, jsonl_path.open("w", encoding="utf-8") as js:
        label = "定点音频转写" if clipped else "完整音频逐字转写"
        md.write(f"# {args.title} - {label}\n\n")
        if args.source_url:
            md.write(f"来源：{args.source_url}\n\n")
        if clipped:
            md.write(f"覆盖范围：{timestamp(args.clip_start)} - {timestamp(args.clip_end)}\n\n")
        md.write("说明：由音频自动转写生成，术语、人名和专有名词可能存在误识别，关键引用前请回听核对。\n\n")

        for segment in segments:
            count += 1
            text = segment.text.strip()
            last_end = float(segment.end)
            record = {"start": segment.start, "end": segment.end, "text": text}
            js.write(json.dumps(record, ensure_ascii=False) + "\n")
            md.write(f"[{timestamp(segment.start)} - {timestamp(segment.end)}] {text}\n\n")
            if count % 100 == 0:
                print(f"progress {timestamp(last_end)} segments={count}", flush=True)

    print(f"Done. segments={count} end={timestamp(last_end)} md={md_path} jsonl={jsonl_path}", flush=True)


if __name__ == "__main__":
    main()
