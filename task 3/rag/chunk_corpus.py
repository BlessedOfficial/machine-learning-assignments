import json
from pathlib import Path

from config import CHUNKS_PATH, USE_AGENTIC_CHUNKER
from rag.citation_meta import citation_fields_for_document
from rag.agentic_chunker import AgenticChunker
from rag.loader import iter_source_files, load_source_text, split_local_chunks, split_paragraphs
from rag.proposition_chunker import extract_propositions
from rag.schemas import ChunkRecord

CHUNKS_FILE = Path(CHUNKS_PATH)
MANIFEST_FILE = CHUNKS_FILE.parent / "manifest.json"


def _chunk_with_citation(
    *,
    chunk_id: str,
    source_file: str,
    doc_text: str,
    paragraph_index: int,
    proposition_index: int,
    text: str,
    chunk_index: int,
    **extra,
) -> ChunkRecord:
    citation = citation_fields_for_document(
        doc_text, source_file, chunk_index=chunk_index
    )
    return ChunkRecord(
        chunk_id=chunk_id,
        source_file=source_file,
        paragraph_index=paragraph_index,
        proposition_index=proposition_index,
        text=text,
        **citation,
        **extra,
    )


def _propositions_for_file(
    source_file: str,
    paragraphs: list[str],
) -> list[str]:
    propositions: list[str] = []
    for paragraph_index, paragraph in enumerate(paragraphs):
        try:
            props = extract_propositions(paragraph)
        except Exception as exc:
            print(f"  Warning: {source_file} p{paragraph_index}: {exc}")
            props = [paragraph]
        if not props:
            props = [paragraph]
        propositions.extend(props)
    return propositions


def _chunks_from_propositions_flat(
    source_file: str,
    stem: str,
    paragraphs: list[str],
    doc_text: str,
) -> list[ChunkRecord]:
    records: list[ChunkRecord] = []
    chunk_counter = 0
    for paragraph_index, paragraph in enumerate(paragraphs):
        try:
            propositions = extract_propositions(paragraph)
        except Exception as exc:
            print(f"  Warning: {source_file} p{paragraph_index}: {exc}")
            propositions = [paragraph]
        if not propositions:
            propositions = [paragraph]

        for proposition_index, proposition in enumerate(propositions):
            records.append(
                _chunk_with_citation(
                    chunk_id=f"{stem}#prop-{paragraph_index:03d}-{proposition_index:02d}",
                    source_file=source_file,
                    doc_text=doc_text,
                    paragraph_index=paragraph_index,
                    proposition_index=proposition_index,
                    text=proposition,
                    chunk_index=chunk_counter,
                    proposition_count=1,
                )
            )
            chunk_counter += 1
    return records


def _chunks_from_local(
    source_file: str,
    stem: str,
    text: str,
) -> list[ChunkRecord]:
    local_chunks = split_local_chunks(text)
    records: list[ChunkRecord] = []
    for chunk_index, chunk_text in enumerate(local_chunks):
        records.append(
            _chunk_with_citation(
                chunk_id=f"{stem}#loc-{chunk_index:03d}",
                source_file=source_file,
                doc_text=text,
                paragraph_index=chunk_index,
                proposition_index=0,
                text=chunk_text,
                chunk_index=chunk_index,
                proposition_count=1,
            )
        )
    return records


def _chunks_from_proposition_list(
    source_file: str,
    stem: str,
    propositions: list[str],
    doc_text: str,
) -> list[ChunkRecord]:
    records: list[ChunkRecord] = []
    for proposition_index, proposition in enumerate(propositions):
        records.append(
            _chunk_with_citation(
                chunk_id=f"{stem}#prop-{proposition_index:03d}",
                source_file=source_file,
                doc_text=doc_text,
                paragraph_index=-1,
                proposition_index=proposition_index,
                text=proposition,
                chunk_index=proposition_index,
                proposition_count=1,
            )
        )
    return records


def _chunks_from_agentic_groups(
    source_file: str,
    stem: str,
    propositions: list[str],
    doc_text: str,
    verbose: bool = False,
) -> list[ChunkRecord]:
    try:
        chunker = AgenticChunker(print_logging=verbose, generate_new_metadata=False)
        chunker.add_propositions(propositions)
    except Exception as exc:
        print(
            f"  Warning: AgenticChunker failed ({exc}); "
            "falling back to one chunk per proposition."
        )
        return _chunks_from_proposition_list(
            source_file, stem, propositions, doc_text
        )

    grouped = chunker.get_chunks(get_type="dict")
    records: list[ChunkRecord] = []

    for _key, data in grouped.items():
        index = data["chunk_index"]
        text = " ".join(data["propositions"])
        records.append(
            _chunk_with_citation(
                chunk_id=f"{stem}#ag-{index:03d}",
                source_file=source_file,
                doc_text=doc_text,
                paragraph_index=-1,
                proposition_index=index,
                text=text,
                chunk_index=index,
                agentic_title=data.get("title"),
                agentic_summary=data.get("summary"),
                agentic_chunk_key=data.get("chunk_id"),
                proposition_count=len(data["propositions"]),
            )
        )

    return records


def chunk_file(
    file_path: Path,
    use_agentic: bool = USE_AGENTIC_CHUNKER,
    use_local: bool = False,
    verbose_agentic: bool = False,
    limit_paragraphs: int | None = None,
) -> list[ChunkRecord]:
    source_file = file_path.name
    stem = file_path.stem
    raw_text = load_source_text(file_path)

    if use_local:
        return _chunks_from_local(source_file, stem, raw_text)

    paragraphs = split_paragraphs(raw_text)

    if limit_paragraphs is not None:
        paragraphs = paragraphs[:limit_paragraphs]

    if use_agentic:
        print(f"  Extracting propositions for agentic grouping...")
        propositions = _propositions_for_file(source_file, paragraphs)
        if not propositions:
            return []
        print(f"  Grouping {len(propositions)} propositions with AgenticChunker...")
        return _chunks_from_agentic_groups(
            source_file,
            stem,
            propositions,
            raw_text,
            verbose=verbose_agentic,
        )

    return _chunks_from_propositions_flat(source_file, stem, paragraphs, raw_text)


def chunk_all_sources(
    limit_files: int | None = None,
    limit_paragraphs_per_file: int | None = None,
    output_path: Path | None = None,
    use_agentic: bool | None = None,
    use_local: bool = False,
    verbose_agentic: bool = False,
) -> list[ChunkRecord]:
    if use_agentic is None:
        use_agentic = USE_AGENTIC_CHUNKER

    output = output_path or CHUNKS_FILE
    output.parent.mkdir(parents=True, exist_ok=True)

    files = iter_source_files()
    if limit_files is not None:
        files = files[:limit_files]

    all_chunks: list[ChunkRecord] = []
    if use_local:
        mode = "local"
    elif use_agentic:
        mode = "llm_proposition_agentic"
    else:
        mode = "llm_proposition"
    stats = {
        "files": 0,
        "paragraphs": 0,
        "chunks": 0,
        "by_file": {},
        "chunking_mode": mode,
    }

    with output.open("w", encoding="utf-8") as out:
        for file_path in files:
            source_file = file_path.name
            print(f"Chunking {source_file}...")
            paragraphs = split_paragraphs(load_source_text(file_path))
            if limit_paragraphs_per_file is not None:
                paragraphs = paragraphs[:limit_paragraphs_per_file]
            stats["paragraphs"] += len(paragraphs)

            file_chunks = chunk_file(
                file_path,
                use_agentic=use_agentic,
                use_local=use_local,
                verbose_agentic=verbose_agentic,
                limit_paragraphs=limit_paragraphs_per_file,
            )

            for chunk in file_chunks:
                out.write(chunk.model_dump_json() + "\n")

            all_chunks.extend(file_chunks)
            stats["files"] += 1
            stats["chunks"] += len(file_chunks)
            stats["by_file"][source_file] = len(file_chunks)
            if use_local:
                label = "local chunks"
            elif use_agentic:
                label = "agentic groups"
            else:
                label = "propositions"
            print(f"  -> {len(file_chunks)} {label}")

    manifest = {
        "hub_prompt": None if use_local else "wfh/proposal-indexing",
        "chunking": mode,
        "agentic_chunker": use_agentic and not use_local,
        "output": str(output),
        **stats,
    }
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nWrote {stats['chunks']} chunks from {stats['files']} files to {output}")
    return all_chunks


def load_chunks(path: Path | None = None) -> list[ChunkRecord]:
    chunks_path = path or CHUNKS_FILE
    if not chunks_path.exists():
        return []

    records: list[ChunkRecord] = []
    with chunks_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(ChunkRecord.model_validate_json(line))
    return records
