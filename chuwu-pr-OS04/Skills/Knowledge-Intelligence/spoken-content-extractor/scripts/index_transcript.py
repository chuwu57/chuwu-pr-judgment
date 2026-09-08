#!/usr/bin/env python3
"""Build, verify and search a lossless chunk index for timestamped transcript JSONL."""

import argparse
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path


WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_+.-]*|[\u3400-\u9fff]+")


def timestamp(seconds: float) -> str:
    seconds = max(0, float(seconds))
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict]:
    records = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"Invalid JSON at {path}:{line_number}: {exc}") from exc
            if not all(key in record for key in ("start", "end", "text")):
                raise SystemExit(f"Missing start/end/text at {path}:{line_number}")
            record["start"] = float(record["start"])
            record["end"] = float(record["end"])
            if record["end"] < record["start"]:
                raise SystemExit(f"end < start at {path}:{line_number}")
            records.append(record)
    if not records:
        raise SystemExit(f"No transcript records in {path}")
    return records


def split_chunks(records: list[dict], chunk_seconds: int) -> list[list[tuple[int, dict]]]:
    chunks: list[list[tuple[int, dict]]] = []
    current: list[tuple[int, dict]] = []
    anchor = records[0]["start"]
    for index, record in enumerate(records, 1):
        if current and record["start"] >= anchor + chunk_seconds:
            chunks.append(current)
            current = []
            anchor = record["start"]
        current.append((index, record))
    if current:
        chunks.append(current)
    return chunks


def build(args: argparse.Namespace) -> None:
    source = Path(args.jsonl).expanduser().resolve()
    if not source.is_file():
        raise SystemExit(f"Transcript JSONL not found: {source}")
    out_dir = Path(args.out_dir).expanduser().resolve()
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SystemExit(f"Output directory must be empty or absent: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    records = load_jsonl(source)
    chunks = split_chunks(records, args.chunk_seconds)
    manifest_chunks = []

    for chunk_number, chunk in enumerate(chunks, 1):
        chunk_id = f"chunk-{chunk_number:04d}"
        md_name = f"{chunk_id}.md"
        jsonl_name = f"{chunk_id}.jsonl"
        md_path = out_dir / md_name
        jsonl_path = out_dir / jsonl_name
        first_index, first = chunk[0]
        last_index, last = chunk[-1]
        text_chars = sum(len(str(record.get("text", ""))) for _, record in chunk)

        with md_path.open("w", encoding="utf-8") as md, jsonl_path.open("w", encoding="utf-8") as js:
            md.write(f"# {chunk_id}｜{timestamp(first['start'])}–{timestamp(last['end'])}\n\n")
            md.write(f"来源JSONL：{source}\n\n")
            for segment_index, record in chunk:
                speaker = str(record.get("speaker", "")).strip()
                speaker_prefix = f"{speaker}｜" if speaker else ""
                md.write(
                    f"[{timestamp(record['start'])} - {timestamp(record['end'])}] "
                    f"{speaker_prefix}{str(record.get('text', '')).strip()}\n\n"
                )
                js.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")

        manifest_chunks.append(
            {
                "id": chunk_id,
                "path": md_name,
                "jsonl_path": jsonl_name,
                "start": first["start"],
                "end": last["end"],
                "segment_start": first_index,
                "segment_end": last_index,
                "segment_count": len(chunk),
                "text_chars": text_chars,
            }
        )

    index = {
        "format": "transcript-chunk-index-v1",
        "source_jsonl": str(source),
        "source_sha256": file_sha256(source),
        "chunk_seconds": args.chunk_seconds,
        "segment_count": len(records),
        "text_chars": sum(len(str(record.get("text", ""))) for record in records),
        "start": records[0]["start"],
        "end": max(record["end"] for record in records),
        "chunks": manifest_chunks,
    }
    index_path = out_dir / "index.json"
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "index": str(index_path),
                "segments": len(records),
                "chunks": len(chunks),
                "end": timestamp(index["end"]),
                "source_sha256": index["source_sha256"],
            },
            ensure_ascii=False,
        )
    )


def load_index(path: Path) -> dict:
    index = json.loads(path.read_text(encoding="utf-8"))
    if index.get("format") != "transcript-chunk-index-v1":
        raise SystemExit(f"Unsupported index format: {index.get('format')}")
    return index


def verify(args: argparse.Namespace) -> None:
    index_path = Path(args.index).expanduser().resolve()
    index = load_index(index_path)
    source = Path(index["source_jsonl"])
    if not source.is_file():
        raise SystemExit(f"Source JSONL not found: {source}")
    if file_sha256(source) != index["source_sha256"]:
        raise SystemExit("Source JSONL hash no longer matches the index")

    source_records = load_jsonl(source)
    chunk_records = []
    expected_segment = 1
    for chunk in index["chunks"]:
        if chunk["segment_start"] != expected_segment:
            raise SystemExit(f"Non-contiguous segment range at {chunk['id']}")
        chunk_path = index_path.parent / chunk["jsonl_path"]
        records = load_jsonl(chunk_path)
        if len(records) != chunk["segment_count"]:
            raise SystemExit(f"Segment count mismatch at {chunk['id']}")
        chunk_records.extend(records)
        expected_segment = chunk["segment_end"] + 1

    if source_records != chunk_records:
        raise SystemExit("Chunk JSONL does not reproduce every source segment in order")
    if len(source_records) != index["segment_count"]:
        raise SystemExit("Index segment_count mismatch")
    print(
        json.dumps(
            {
                "status": "passed",
                "segments": len(source_records),
                "chunks": len(index["chunks"]),
                "source_sha256": index["source_sha256"],
            },
            ensure_ascii=False,
        )
    )


def terms(text: str) -> list[str]:
    output = []
    for token in WORD_RE.findall(text.lower()):
        if re.fullmatch(r"[\u3400-\u9fff]+", token):
            output.append(token)
            if len(token) > 1:
                output.extend(token[index : index + 2] for index in range(len(token) - 1))
        elif len(token) > 1 or token.isdigit():
            output.append(token)
    return output


def best_snippet(text: str, query: str, query_terms: set[str], max_chars: int) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip() and not line.startswith("#")]
    if not lines:
        return ""
    lowered_query = query.lower()

    def line_score(line: str) -> tuple[int, int]:
        lowered = line.lower()
        exact = 100 if lowered_query and lowered_query in lowered else 0
        overlap = sum(lowered.count(term) for term in query_terms)
        return exact + overlap, -len(line)

    selected = max(lines, key=line_score)
    if len(selected) <= max_chars:
        return selected
    lowered = selected.lower()
    positions = [lowered.find(term) for term in query_terms if lowered.find(term) >= 0]
    center = min(positions) if positions else 0
    start = max(0, center - max_chars // 3)
    end = min(len(selected), start + max_chars)
    return ("…" if start else "") + selected[start:end] + ("…" if end < len(selected) else "")


def search(args: argparse.Namespace) -> None:
    index_path = Path(args.index).expanduser().resolve()
    index = load_index(index_path)
    documents = []
    for chunk in index["chunks"]:
        path = index_path.parent / chunk["path"]
        text = path.read_text(encoding="utf-8")
        transcript_text = "\n".join(line for line in text.splitlines() if line.startswith("["))
        documents.append((chunk, path, transcript_text, Counter(terms(transcript_text))))

    query_terms = terms(args.query)
    if not query_terms:
        raise SystemExit("Query contains no searchable terms")
    document_frequency = Counter()
    for _, _, _, counts in documents:
        document_frequency.update(counts.keys())
    total_documents = len(documents)
    query_counts = Counter(query_terms)
    results = []
    for chunk, path, text, counts in documents:
        score = 0.0
        for term, query_frequency in query_counts.items():
            frequency = counts.get(term, 0)
            if not frequency:
                continue
            inverse_frequency = math.log((total_documents + 1) / (document_frequency[term] + 0.5)) + 1
            score += (1 + math.log(frequency)) * inverse_frequency * query_frequency
        if args.query.lower() in text.lower():
            score += 8.0
        if score <= 0:
            continue
        results.append(
            {
                "id": chunk["id"],
                "path": str(path),
                "start": timestamp(chunk["start"]),
                "end": timestamp(chunk["end"]),
                "score": round(score, 3),
                "snippet": best_snippet(text, args.query, set(query_terms), args.snippet_chars),
            }
        )
    results.sort(key=lambda item: (-item["score"], item["start"]))
    print(json.dumps({"query": args.query, "matches": results[: args.limit]}, ensure_ascii=False, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="Build lossless Markdown/JSONL chunks and index.json.")
    build_parser.add_argument("--jsonl", required=True, help="Timestamped source transcript JSONL.")
    build_parser.add_argument("--out-dir", required=True, help="Empty or absent output directory.")
    build_parser.add_argument("--chunk-seconds", type=int, default=300, help="Target chunk duration.")
    build_parser.set_defaults(handler=build)

    verify_parser = subparsers.add_parser("verify", help="Verify source hash and exact segment coverage.")
    verify_parser.add_argument("--index", required=True, help="Path to index.json.")
    verify_parser.set_defaults(handler=verify)

    search_parser = subparsers.add_parser("search", help="Return only transcript chunks relevant to a query.")
    search_parser.add_argument("--index", required=True, help="Path to index.json.")
    search_parser.add_argument("--query", required=True, help="Words or phrase to find.")
    search_parser.add_argument("--limit", type=int, default=6, help="Maximum matching chunks.")
    search_parser.add_argument("--snippet-chars", type=int, default=280, help="Maximum snippet characters per match.")
    search_parser.set_defaults(handler=search)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if getattr(args, "chunk_seconds", 1) <= 0:
        raise SystemExit("--chunk-seconds must be positive")
    if getattr(args, "limit", 1) <= 0:
        raise SystemExit("--limit must be positive")
    args.handler(args)


if __name__ == "__main__":
    main()
