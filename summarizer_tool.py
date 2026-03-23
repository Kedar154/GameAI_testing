from __future__ import annotations
import json, re, textwrap
from dataclasses import dataclass, field
from typing import List

import anthropic
from langchain_core.tools import tool


# ── Standard envelope ────────────────────────────────────────────────────────
def _ok(data: dict) -> str: return json.dumps({"status": "ok",    "data": data, "error": None})
def _err(msg: str)  -> str: return json.dumps({"status": "error", "data": {},   "error": msg})


# ── Data structures (unchanged) ──────────────────────────────────────────────
@dataclass
class NPCSummary:
    behavior: str = ""
    topics_discussed: List[str] = field(default_factory=list)
    key_context: str = ""

    def to_dict(self):
        return {"behavior": self.behavior, "topics_discussed": self.topics_discussed, "key_context": self.key_context}

    @staticmethod
    def from_dict(d):
        return NPCSummary(behavior=d.get("behavior", ""), topics_discussed=d.get("topics_discussed", []), key_context=d.get("key_context", ""))


@dataclass
class NarrativeMemoryInput:
    npc_name: str
    existing_canon: List[str]
    previous_summary: NPCSummary
    latest_conversation: str

    def to_dict(self):
        return {"npc_name": self.npc_name, "existing_canon": self.existing_canon,
                "previous_summary": self.previous_summary.to_dict(), "latest_conversation": self.latest_conversation}


@dataclass
class NarrativeMemoryOutput:
    npc: str
    new_canon_facts: List[str]
    updated_summary: NPCSummary

    def to_dict(self):
        return {"npc": self.npc, "new_canon_facts": self.new_canon_facts, "updated_summary": self.updated_summary.to_dict()}


# ── System prompt (unchanged) ────────────────────────────────────────────────
_SYSTEM_PROMPT = textwrap.dedent("""
You are NarrativeMemoryEngine — a strict memory system for maintaining NPC consistency in a detective game.
You are NOT a storyteller. You are a deterministic memory processor.

## MEMORY LAYERS

1. CANON (IMMUTABLE FACTS)
- Atomic, specific, past-tense, unambiguous facts only
- NEVER modify or repeat existing canon
- Contradictions → DO NOT add to canon, log in summary instead

2. SUMMARY (MUTABLE CONTEXT) — max 450 chars key_context
- behavior: emotional tone + progression
- topics_discussed: new topics only
- key_context: latest facts, [CONTRADICTION] markers, unresolved threads, player knowledge

Consistency > Completeness. Precision > Creativity. Never hallucinate.
""").strip()


# ── Engine (unchanged logic, singleton instance) ─────────────────────────────
class NarrativeMemoryEngine:
    MODEL = "claude-sonnet-4-20250514"
    MAX_TOKENS = 1200
    MAX_CONTEXT_CHARS = 450

    def __init__(self, client: anthropic.Anthropic):
        self.client = client

    def process(self, data: NarrativeMemoryInput) -> NarrativeMemoryOutput:
        for attempt in range(2):
            try:
                raw = self._call_llm(self._build_user_message(data))
                if not raw: raise ValueError("Empty response")
                return self._parse_response(raw, data.npc_name, data.existing_canon, data.previous_summary)
            except Exception as e:
                print(f"[MemoryEngine] Attempt {attempt+1}: {e}")
                if attempt == 1:
                    return NarrativeMemoryOutput(npc=data.npc_name, new_canon_facts=[], updated_summary=data.previous_summary)

    def _build_user_message(self, data: NarrativeMemoryInput) -> str:
        return "Process the following NPC memory update.\n\nINPUT:\n" + json.dumps(data.to_dict(), indent=2, ensure_ascii=False)

    def _call_llm(self, user_message: str) -> str:
        response = self.client.messages.create(
            model=self.MODEL, max_tokens=self.MAX_TOKENS, system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}]
        )
        return "".join(b.text for b in response.content if hasattr(b, "text")).strip()

    @staticmethod
    def _normalize(fact: str) -> str:
        return re.sub(r'[^\w\s]', '', fact.strip().lower())

    def _parse_response(self, raw_text, npc_name, existing_canon, previous_summary) -> NarrativeMemoryOutput:
        try:
            json_str, _ = self._extract_json(raw_text)
            parsed = json.loads(json_str)
        except Exception:
            return NarrativeMemoryOutput(npc=npc_name, new_canon_facts=[], updated_summary=previous_summary)

        existing_norm = {self._normalize(f) for f in existing_canon}
        deduped = [f for f in parsed.get("new_canon_facts", []) if self._normalize(f) not in existing_norm]

        s = parsed.get("updated_summary")
        if not isinstance(s, dict): s = previous_summary.to_dict()
        s.setdefault("behavior",         previous_summary.behavior)
        s.setdefault("topics_discussed", previous_summary.topics_discussed)
        s.setdefault("key_context",      previous_summary.key_context)
        s["topics_discussed"] = list(dict.fromkeys(s["topics_discussed"]))
        kc = s.get("key_context", "")
        if len(kc) > self.MAX_CONTEXT_CHARS: kc = kc[:self.MAX_CONTEXT_CHARS].rstrip() + "…"
        s["key_context"] = kc

        return NarrativeMemoryOutput(npc=parsed.get("npc", npc_name), new_canon_facts=deduped, updated_summary=NPCSummary.from_dict(s))

    @staticmethod
    def _extract_json(text: str) -> tuple[str, str]:
        start = text.find("{")
        if start == -1: raise ValueError("No JSON found")
        depth, in_str, esc = 0, False, False
        for i in range(start, len(text)):
            ch = text[i]
            if esc:                   esc = False; continue
            if ch == "\\" and in_str: esc = True;  continue
            if ch == '"':             in_str = not in_str; continue
            if in_str:                continue
            if ch == "{":             depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0: return text[start:i+1], text[i+1:]
        raise ValueError("Unbalanced JSON")


# ── Original state functions (unchanged) ─────────────────────────────────────
def update_state(db: dict, output: NarrativeMemoryOutput) -> dict:
    npc = output.npc
    if npc not in db or not isinstance(db[npc], dict):
        db[npc] = {"canon": [], "summary": {}}
    db[npc].setdefault("canon", [])
    existing = {f.lower() for f in db[npc]["canon"]}
    for fact in output.new_canon_facts:
        if fact.lower() not in existing:
            db[npc]["canon"].append(fact)
            existing.add(fact.lower())
    db[npc]["summary"] = output.updated_summary.to_dict()
    return db

def get_npc_state(db: dict, npc_name: str) -> dict:
    npc_data = db.get(npc_name, {})
    return {"npc": npc_name, "canon": npc_data.get("canon", []), "summary": npc_data.get("summary", {})}


# ── Singleton ─────────────────────────────────────────────────────────────────
_engine = NarrativeMemoryEngine(client=anthropic.Anthropic())


# =============================================================================
# ─── TOOLS ───────────────────────────────────────────────────────────────────
# =============================================================================

@tool
def get_npc_memory(npc_id: str, session_id: str, player_id: str, payload: str) -> str:
    """
    When to call: at the start of any NPC interaction.
    Reads canon facts and summary for this NPC from the database.

    payload fields:
      - db (dict): state["npc_db"]

    Returns: canon (list), summary (dict)
    """
    try:
        p = json.loads(payload)
        if "db" not in p: return _err("Missing: db")
        result = get_npc_state(p["db"], npc_id)
        return _ok({"npc_id": npc_id, "canon": result["canon"], "summary": result["summary"]})
    except Exception as e:
        return _err(str(e))


@tool
def process_npc_memory(npc_id: str, session_id: str, player_id: str, payload: str) -> str:
    """
    When to call: after NPC conversation ends, or every 6-8 turns.
    Extracts new canon facts + updates summary from latest dialogue.

    payload fields:
      - latest_conversation (str):  raw dialogue 'Player: ...\nNPC: ...'
      - existing_canon      (list): state canon facts for this NPC
      - previous_summary    (dict): state summary for this NPC

    Returns: new_canon_facts (list), updated_summary (dict)
    """
    try:
        p = json.loads(payload)
        missing = [k for k in ("latest_conversation", "existing_canon", "previous_summary") if k not in p]
        if missing: return _err(f"Missing: {missing}")

        result = _engine.process(NarrativeMemoryInput(
            npc_name=npc_id,
            existing_canon=p["existing_canon"],
            previous_summary=NPCSummary.from_dict(p["previous_summary"]),
            latest_conversation=p["latest_conversation"],
        ))
        return _ok({"npc_id": result.npc, "new_canon_facts": result.new_canon_facts, "updated_summary": result.updated_summary.to_dict()})
    except Exception as e:
        return _err(str(e))


@tool
def compress_short_term_memory(npc_id: str, session_id: str, player_id: str, payload: str) -> str:
    """
    When to call: when turn_count >= 8 (needs_summary = True in state).
    Compresses raw short-term turns into summary. Does NOT add to canon.

    payload fields:
      - raw_turns        (list[str]): state short_term[npc_id]
      - existing_summary (dict):     state npc_summaries[npc_id]

    Returns: updated_summary (dict), clear_short_term=True, reset_turn_count=True
    """
    try:
        p = json.loads(payload)
        missing = [k for k in ("raw_turns", "existing_summary") if k not in p]
        if missing: return _err(f"Missing: {missing}")
        if not p["raw_turns"]: return _err("raw_turns is empty")

        result = _engine.process(NarrativeMemoryInput(
            npc_name=npc_id,
            existing_canon=[],
            previous_summary=NPCSummary.from_dict(p["existing_summary"]),
            latest_conversation="\n".join(p["raw_turns"]),
        ))
        return _ok({"npc_id": npc_id, "updated_summary": result.updated_summary.to_dict(), "clear_short_term": True, "reset_turn_count": True})
    except Exception as e:
        return _err(str(e))


@tool
def update_npc_db(npc_id: str, session_id: str, player_id: str, payload: str) -> str:
    """
    When to call: immediately after process_npc_memory succeeds.
    Persists new canon facts and updated summary into the database.

    payload fields:
      - db              (dict):      state["npc_db"]
      - new_canon_facts (list[str]): from process_npc_memory output
      - updated_summary (dict):      from process_npc_memory output

    Returns: db (dict) — write back to state["npc_db"], facts_added (int)
    """
    try:
        p = json.loads(payload)
        missing = [k for k in ("db", "new_canon_facts", "updated_summary") if k not in p]
        if missing: return _err(f"Missing: {missing}")

        dummy = NarrativeMemoryOutput(
            npc=npc_id,
            new_canon_facts=p["new_canon_facts"],
            updated_summary=NPCSummary.from_dict(p["updated_summary"]),
        )
        before = len(p["db"].get(npc_id, {}).get("canon", []))
        updated_db = update_state(p["db"], dummy)
        after = len(updated_db.get(npc_id, {}).get("canon", []))

        return _ok({"db": updated_db, "facts_added": after - before})
    except Exception as e:
        return _err(str(e))


# ── Export ────────────────────────────────────────────────────────────────────
MEMORY_TOOLS = [
    get_npc_memory,              # read   — start of NPC interaction
    process_npc_memory,          # main   — after conversation / every 6-8 turns
    compress_short_term_memory,  # compress — when turn_count >= 8
    update_npc_db,               # write  — after process_npc_memory
]
