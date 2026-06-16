"""
Agentic chunking: group atomic propositions into semantically related chunks.

Adapted from FullStackRetrieval RetrievalTutorials (agentic_chunker.py).
Uses OpenRouter via langchain_openai ChatOpenAI.
"""

import re
import uuid
from typing import Any, Literal

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from config import CHUNKING_MODEL, OPENROUTER_API_KEY, OPENROUTER_BASE_URL
from utils.openrouter_retry import invoke_with_retry


class AgenticChunker:
    def __init__(
        self,
        llm: ChatOpenAI | None = None,
        generate_new_metadata: bool = True,
        print_logging: bool = False,
    ):
        self.chunks: dict[str, dict] = {}
        self.id_truncate_limit = 5
        self.generate_new_metadata_ind = generate_new_metadata
        self.print_logging = print_logging

        if llm is None:
            if not OPENROUTER_API_KEY:
                raise ValueError("OPENROUTER_API_KEY is required for AgenticChunker.")
            llm = ChatOpenAI(
                model=CHUNKING_MODEL,
                api_key=OPENROUTER_API_KEY,
                base_url=OPENROUTER_BASE_URL,
                temperature=0,
                max_retries=2,
                timeout=120,
            )
        self.llm = llm

    def _invoke_chain(self, chain: Any, inputs: dict[str, Any], *, label: str) -> Any:
        return invoke_with_retry(chain, inputs, label=label)

    @staticmethod
    def _clean_llm_text(text: str) -> str:
        if not text:
            return ""
        return text.replace("</assistant>", "").strip().strip("\n")

    def reset(self) -> None:
        self.chunks = {}

    def add_propositions(self, propositions: list[str]) -> None:
        for proposition in propositions:
            prop = proposition.strip()
            if prop:
                self.add_proposition(prop)

    def add_proposition(self, proposition: str) -> None:
        if self.print_logging:
            print(f"\nAdding: '{proposition[:80]}...'")

        if not self.chunks:
            if self.print_logging:
                print("No chunks, creating a new one")
            self._create_new_chunk(proposition)
            return

        chunk_id = self._find_relevant_chunk(proposition)
        if chunk_id and chunk_id in self.chunks:
            if self.print_logging:
                title = self.chunks[chunk_id]["title"]
                print(f"Chunk found ({chunk_id}), adding to: {title}")
            self._add_proposition_to_chunk(chunk_id, proposition)
            return

        if self.print_logging:
            print("No matching chunk, creating new one")
        self._create_new_chunk(proposition)

    def _add_proposition_to_chunk(self, chunk_id: str, proposition: str) -> None:
        self.chunks[chunk_id]["propositions"].append(proposition)
        if self.generate_new_metadata_ind:
            self.chunks[chunk_id]["summary"] = self._update_chunk_summary(
                self.chunks[chunk_id]
            )
            self.chunks[chunk_id]["title"] = self._update_chunk_title(
                self.chunks[chunk_id]
            )

    def _update_chunk_summary(self, chunk: dict) -> str:
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You steward groups of related propositions. Write one brief sentence "
                    "summarizing what this chunk is about. Generalize when appropriate. "
                    "Respond with only the summary.",
                ),
                (
                    "user",
                    "Propositions:\n{proposition}\n\nCurrent summary:\n{current_summary}",
                ),
            ]
        )
        result = self._invoke_chain(
            prompt | self.llm,
            {
                "proposition": "\n".join(chunk["propositions"]),
                "current_summary": chunk["summary"],
            },
            label="AgenticChunker summary",
        )
        return self._clean_llm_text(result.content or chunk["summary"])

    def _update_chunk_title(self, chunk: dict) -> str:
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Write a very brief chunk title (few words) for this group of propositions. "
                    "Respond with only the title.",
                ),
                (
                    "user",
                    "Propositions:\n{proposition}\n\nSummary:\n{current_summary}\n\n"
                    "Current title:\n{current_title}",
                ),
            ]
        )
        result = self._invoke_chain(
            prompt | self.llm,
            {
                "proposition": "\n".join(chunk["propositions"]),
                "current_summary": chunk["summary"],
                "current_title": chunk["title"],
            },
            label="AgenticChunker title",
        )
        return self._clean_llm_text(result.content or chunk["title"])

    def _get_new_chunk_summary(self, proposition: str) -> str:
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Write one brief sentence summarizing what this new chunk group is about. "
                    "Respond with only the summary.",
                ),
                ("user", "Proposition:\n{proposition}"),
            ]
        )
        result = self._invoke_chain(
            prompt | self.llm,
            {"proposition": proposition},
            label="AgenticChunker new summary",
        )
        return self._clean_llm_text(result.content or "")

    def _get_new_chunk_title(self, summary: str) -> str:
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Write a very brief chunk title for this summary. Respond with only the title.",
                ),
                ("user", "Summary:\n{summary}"),
            ]
        )
        result = self._invoke_chain(
            prompt | self.llm,
            {"summary": summary},
            label="AgenticChunker new title",
        )
        return self._clean_llm_text(result.content or "Untitled")

    def _create_new_chunk(self, proposition: str) -> None:
        new_chunk_id = str(uuid.uuid4())[: self.id_truncate_limit]
        summary = self._get_new_chunk_summary(proposition)
        title = self._get_new_chunk_title(summary)

        self.chunks[new_chunk_id] = {
            "chunk_id": new_chunk_id,
            "propositions": [proposition],
            "title": title,
            "summary": summary,
            "chunk_index": len(self.chunks),
        }
        if self.print_logging:
            print(f"Created chunk ({new_chunk_id}): {title}")

    def get_chunk_outline(self) -> str:
        parts = []
        for chunk in self.chunks.values():
            parts.append(
                f"Chunk ID: {chunk['chunk_id']}\n"
                f"Chunk Name: {chunk['title']}\n"
                f"Chunk Summary: {chunk['summary']}\n"
            )
        return "\n".join(parts)

    def _find_relevant_chunk(self, proposition: str) -> str | None:
        if not self.chunks:
            return None

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Determine if the Proposition belongs to any existing chunk "
                    "(similar meaning or topic). Return only the chunk id, or 'No chunks' if none fit.",
                ),
                (
                    "user",
                    "Current chunks:\n{current_chunk_outline}\n\nProposition:\n{proposition}",
                ),
            ]
        )
        result = self._invoke_chain(
            prompt | self.llm,
            {
                "proposition": proposition,
                "current_chunk_outline": self.get_chunk_outline(),
            },
            label="AgenticChunker match",
        )
        response = result.content or ""
        return self._parse_chunk_id_from_response(response)

    def _parse_chunk_id_from_response(self, response: str) -> str | None:
        lower = response.lower().strip()
        if "no chunks" in lower or "no chunk" in lower:
            return None

        for cid in self.chunks:
            if cid in response:
                return cid

        match = re.search(r"\b[a-f0-9]{5}\b", response.lower())
        if match and match.group() in self.chunks:
            return match.group()

        return None

    def get_chunks(
        self, get_type: Literal["dict", "list_of_strings"] = "dict"
    ) -> dict | list[str]:
        if get_type == "dict":
            return self.chunks
        return [" ".join(chunk["propositions"]) for chunk in self.chunks.values()]

    def pretty_print_chunks(self) -> None:
        print(f"\n{len(self.chunks)} agentic chunks\n")
        for chunk in self.chunks.values():
            print(f"#{chunk['chunk_index']} {chunk['title']} ({chunk['chunk_id']})")
            print(f"  {chunk['summary']}")
            for prop in chunk["propositions"]:
                print(f"   - {prop[:100]}")
            print()
