from __future__ import annotations

import json
import textwrap
import re
from dataclasses import dataclass, field
from typing import List
 
import anthropic
 
 
# =============================================================================
# ─── DATA STRUCTURES ─────────────────────────────────────────────────────────
# =============================================================================
 
@dataclass
class NPCSummary:
    """
    Mutable context layer for a single NPC.
 
    This is the ONLY long-term compressed memory in the system.
    Losing fields here = permanent information loss.
    """
    behavior: str = ""
    """Emotional/behavioral tone: e.g. 'nervous', 'evasive', 'cooperative'."""
 
    topics_discussed: List[str] = field(default_factory=list)
    """Flat list of interrogation topics covered so far."""
 
    key_context: str = ""
    """
    Free-form compressed narrative context.
    Must preserve: revealed facts, lies told, player's current knowledge,
    unresolved threads, and relationship dynamics.
    """
 
    def to_dict(self) -> dict:
        return {
            "behavior": self.behavior,
            "topics_discussed": self.topics_discussed,
            "key_context": self.key_context,
        }
 
    @staticmethod
    def from_dict(d: dict) -> "NPCSummary":
        return NPCSummary(
            behavior=d.get("behavior", ""),
            topics_discussed=d.get("topics_discussed", []),
            key_context=d.get("key_context", ""),
        )
 
 
@dataclass
class NarrativeMemoryInput:
    """
    Full input contract for one NarrativeMemoryEngine.process() call.
 
    The Officer Agent must populate all fields before calling the tool.
    """
    npc_name: str
    """Canonical NPC identifier used throughout the game. E.g. 'Arjun Mehta'."""
 
    existing_canon: List[str]
    """
    All facts committed by this NPC in previous sessions.
    Fetched by the Caching Tool before this call.
    NEVER modified by the caller — the engine returns additions only.
    """
 
    previous_summary: NPCSummary
    """
    Last saved NPCSummary for this NPC.
    Replaced entirely after processing — the engine returns the new version.
    """
 
    latest_conversation: str
    """
    Full raw dialogue from the most recent player ↔ NPC interaction.
    Format: free-form text, typically 'Player: ...\n{npc_name}: ...\n...'
    """
 
    def to_dict(self) -> dict:
        return {
            "npc_name": self.npc_name,
            "existing_canon": self.existing_canon,
            "previous_summary": self.previous_summary.to_dict(),
            "latest_conversation": self.latest_conversation,
        }
 
 
@dataclass
class NarrativeMemoryOutput:
    """
    Full output contract returned by NarrativeMemoryEngine.process().
 
    The Officer Agent / Caching Tool must:
      1. APPEND  new_canon_facts  → existing_canon in the DB
      2. REPLACE previous_summary → updated_summary in the DB
    """
    npc: str
    """NPC name — mirrors input for traceability."""
 
    new_canon_facts: List[str]
    """
    Net-new atomic facts extracted from latest_conversation.
    Empty list [] if nothing new was committed.
    """
 
    updated_summary: NPCSummary
    """
    Fully merged summary replacing the previous one.
    Contains updated behavior, topics, and key_context.
    """
 
    def to_dict(self) -> dict:
        return {
            "npc": self.npc,
            "new_canon_facts": self.new_canon_facts,
            "updated_summary": self.updated_summary.to_dict(),
        }
 
 
# =============================================================================
# ─── SYSTEM PROMPT ───────────────────────────────────────────────────────────
# =============================================================================
 
_SYSTEM_PROMPT = textwrap.dedent("""
You are NarrativeMemoryEngine — a strict memory system for maintaining NPC consistency in a detective game.

You are NOT a storyteller. You are a deterministic memory processor.

--------------------------------
## MEMORY LAYERS

1. CANON (IMMUTABLE FACTS)
- Stores what the NPC has COMMITTED to saying (truth or lie)
- Each fact must be:
  • Atomic (one fact only)
  • Specific (must include time, action, or location)
  • Clear and unambiguous
  • Written in past tense
- NEVER modify or repeat existing canon
- If a new statement contradicts existing canon:
  → DO NOT add it to canon
  → Log it in summary as a contradiction

2. SUMMARY (MUTABLE CONTEXT)
This is the ONLY long-term memory. Losing important info is NOT allowed.

Structure:
{
  "behavior": "...",
  "topics_discussed": [...],
  "key_context": "..."
}

Rules:
- behavior:
  • Capture emotional tone AND progression

- topics_discussed:
  • Add ONLY new topics

- key_context (MAX 450 chars):
  MUST ALWAYS include:
  • Latest important facts revealed
  • Any contradictions (use [CONTRADICTION] marker)
  • Unresolved mysteries
  • Player knowledge progression

--------------------------------
## FINAL RULE
Consistency > Completeness  
Precision > Creativity  
Stability > Fluency

Never hallucinate. Never guess.
""").strip()
 
 
# =============================================================================
# ─── NARRATIVE MEMORY ENGINE TOOL ────────────────────────────────────────────
# =============================================================================
 
class NarrativeMemoryEngine:
    
    MODEL: str = "claude-sonnet-4-20250514"
    MAX_TOKENS: int = 1200
    MAX_CONTEXT_CHARS: int = 450
 
    def __init__(self, client: anthropic.Anthropic) -> None:
        self.client = client
 
    # PUBLIC API
    # ────────────────────────────────────────────────────────────────────
 
    def process(self, data: NarrativeMemoryInput) -> NarrativeMemoryOutput:
        for attempt in range(2):
            try:
                user_message = self._build_user_message(data)
                raw_response = self._call_llm(user_message)

                if not raw_response:
                    raise ValueError("Empty response from LLM")

                return self._parse_response(
                    raw_response,
                    data.npc_name,
                    data.existing_canon,
                    data.previous_summary
                )

            except Exception as e:
                print(f"[MemoryEngine Error] Attempt {attempt+1}: {e}")
                if attempt == 1:
                    # fallback safe return
                    return NarrativeMemoryOutput(
                        npc=data.npc_name,
                        new_canon_facts=[],
                        updated_summary=data.previous_summary
                    )
 
    # PRIVATE: MESSAGE BUILDER
    # ─────────────────────────────────────────────────────────────────────
 
    def _build_user_message(self, data: NarrativeMemoryInput) -> str:
        payload = data.to_dict()
        return (
            "Process the following NPC memory update.\n\n"
            "INPUT:\n"
            + json.dumps(payload, indent=2, ensure_ascii=False)
        )
 
    # PRIVATE: LLM CALL
    # ─────────────────────────────────────────────────────────────────────
 
    def _call_llm(self, user_message: str) -> str:
        response = self.client.messages.create(
            model=self.MODEL,
            max_tokens=self.MAX_TOKENS,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        return "".join(
            block.text for block in response.content if hasattr(block, "text")
        ).strip()
 
    # PRIVATE: RESPONSE PARSER
    # ─────────────────────────────────────────────────────────────────────
 
    @staticmethod
    def _normalize_fact(fact: str) -> str:
        fact = fact.strip().lower()
        fact = re.sub(r'[^\w\s]', '', fact)
        return fact
 
    def _parse_response(
        self,
        raw_text: str,
        npc_name: str,
        existing_canon: List[str],
        previous_summary: NPCSummary,
    ) -> NarrativeMemoryOutput:
 
        try:
            json_str, _ = self._extract_json_and_explanation(raw_text)
            parsed = json.loads(json_str)
        except Exception:
            return NarrativeMemoryOutput(
                npc=npc_name,
                new_canon_facts=[],
                updated_summary=previous_summary
            )
 
        # Canon deduplication
        existing_normalized = {self._normalize_fact(f) for f in existing_canon}
        deduplicated_facts = [
            f for f in parsed.get("new_canon_facts", [])
            if self._normalize_fact(f) not in existing_normalized
        ]
 
        # Summary validation
        summary_dict = parsed.get("updated_summary")
        if not isinstance(summary_dict, dict):
            summary_dict = previous_summary.to_dict()

        summary_dict.setdefault("behavior", previous_summary.behavior)
        summary_dict.setdefault("topics_discussed", previous_summary.topics_discussed)
        summary_dict.setdefault("key_context", previous_summary.key_context)
 
        # Topics deduplication
        raw_topics = summary_dict.get("topics_discussed", [])
        summary_dict["topics_discussed"] = list(dict.fromkeys(raw_topics))
 
        # Context cap
        key_context = summary_dict.get("key_context", "")
        if len(key_context) > self.MAX_CONTEXT_CHARS:
            key_context = key_context[: self.MAX_CONTEXT_CHARS].rstrip() + "…"
        summary_dict["key_context"] = key_context
 
        updated_summary = NPCSummary.from_dict(summary_dict)
 
        return NarrativeMemoryOutput(
            npc=parsed.get("npc", npc_name),
            new_canon_facts=deduplicated_facts,
            updated_summary=updated_summary,
        )
 
    @staticmethod
    def _extract_json_and_explanation(text: str) -> tuple[str, str]:
        start = text.find("{")
        if start == -1:
            raise ValueError("No JSON found")

        depth = 0
        in_string = False
        escape_next = False

        for i in range(start, len(text)):
            ch = text[i]

            if escape_next:
                escape_next = False
                continue
            if ch == "\\" and in_string:
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start:i+1], text[i+1:]

        raise ValueError("Unbalanced JSON")
    

# =============================================================================
# ─── STATE MANAGEMENT ────────────────────────────────────────────────────────
# =============================================================================

def update_state(db: dict, output: NarrativeMemoryOutput) -> dict:
    """
    Safe DB update with deduplication
    """

    npc = output.npc

    if npc not in db or not isinstance(db[npc], dict):
        db[npc] = {"canon": [], "summary": {}}

    db[npc].setdefault("canon", [])
    db[npc].setdefault("summary", {})

    existing = set(f.lower() for f in db[npc]["canon"])

    for fact in output.new_canon_facts:
        if fact.lower() not in existing:
            db[npc]["canon"].append(fact)
            existing.add(fact.lower())

    db[npc]["summary"] = output.updated_summary.to_dict()

    return db


def get_npc_state(db: dict, npc_name: str) -> dict:
    """
    Returns full NPC memory (final usable output)
    """

    npc_data = db.get(npc_name, {})

    return {
        "npc": npc_name,
        "canon": npc_data.get("canon", []),
        "summary": npc_data.get("summary", {})
    }
