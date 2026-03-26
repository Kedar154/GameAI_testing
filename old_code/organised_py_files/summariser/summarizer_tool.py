from __future__ import annotations
import json, re, textwrap
import anthropic
from langchain_core.tools import tool

_MODEL = "claude-sonnet-4-20250514"
_MAX_TOKENS = 900
_CANON_CAP = 60
_SUMMARY_CAP = 500

_client = anthropic.Anthropic()

_SYSTEM = textwrap.dedent("""
You are a strict NPC memory processor for a detective game.
you have to convert the given input into the following
you will be given an npc id and the 
MEMORY:
1. CANON → atomic, past tense, no duplicates, no contradictions
2. SUMMARY:
   - behavior (≤ 80 chars)
   - topics (new only)
   - key_context (≤ 450 chars)

If contradiction → DO NOT add to canon → mark in summary with [CONTRADICTION]

OUTPUT STRICT JSON:
{
  "new_canon_facts": ["..."],
  "updated_summary": {
    "behavior": "...",
    "topics": ["..."],
    "key_context": "..."
  }
}
""").strip()


@tool
def npc_memory_tool(npc_id: str, payload: dict) -> dict:
    '''
        This tool is to be used after every npc response to summarise the context out of it
        INPUT: 
            npc_id: the is of which npc to refer
            payload: is a dict with the fields
                {
                    "latest_conversation": list[str],
                    "db" : {
                            "canon" : list[str],
                            "summary": {
                                "behavior" : str
                                "topics": str
                                "key_context": str
                            }
                    }
                }
    '''

    if not isinstance(payload, dict):
        return {"status": "error", "error": "payload must be dict", "data": {}}

    if "db" not in payload:
        return {"status": "error", "error": "db missing", "data": {}}

    # mode = payload.get("mode")
    # if mode not in ("read", "update"):
    #     return {"status": "error", "error": "invalid mode", "data": {}}

    db = dict(payload["db"])

    Record = db.get(npc_id, {})
    canon = Record.get("canon", [])
    summary = Record.get("summary", {"behavior": "", "topics": [], "key_context": ""})

    # if mode == "read":
    #     return {
    #         "status": "ok",
    #         "data": {
    #             "npc_id": npc_id,
    #             "canon": canon,
    #             "summary": summary
    #         },
    #         "error": None
    #     }

    conversation = payload.get("latest_conversation", "").strip()
    if not conversation:
        return {"status": "error", "error": "missing conversation", "data": {}}

    try:
        parsed: dict = {}

        response = _client.messages.create(
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            system=_SYSTEM,
            messages=[{
                "role": "user",
                "content": json.dumps({
                    "npc": npc_id,
                    "existing_canon": canon,
                    "current_summary": summary,
                    "latest_conversation": conversation
                }, ensure_ascii=False)
            }]
        )

        raw = "".join(b.text for b in response.content if hasattr(b, "text")).strip()

        start = raw.find("{")
        if start == -1:
            raise ValueError("No JSON")

        depth, in_str, esc = 0, False, False
        for i in range(start, len(raw)):
            ch = raw[i]
            if esc:
                esc = False
                continue
            if ch == "\\" and in_str:
                esc = True
                continue
            if ch == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    parsed = json.loads(raw[start:i+1])
                    break

        def norm(x: str) -> str:
            return re.sub(r"[^\w\s]", "", x.lower())

        existing = {norm(f): f for f in canon}
        for f in parsed.get("new_canon_facts", []):
            k = norm(f)
            if k not in existing:
                existing[k] = f

        new_canon = list(existing.values())[-_CANON_CAP:]

        s = parsed.get("updated_summary", {})

        topics_raw = s.get("topics", [])
        if isinstance(topics_raw, str):
            topics_raw = [topics_raw]

        topics = list(dict.fromkeys(topics_raw))

        behavior = str(s.get("behavior", summary.get("behavior", "")))[:80]
        kc = str(s.get("key_context", summary.get("key_context", "")))

        if len(kc) > _SUMMARY_CAP:
            kc = kc[:_SUMMARY_CAP].rstrip() + "…"

        new_summary = {
            "behavior": behavior,
            "topics": topics,
            "key_context": kc
        }

        db[npc_id] = {
            "canon": new_canon,
            "summary": new_summary
        }

        return {
            "status": "ok",
            "data": {
                "db": db,
                "new_facts": parsed.get("new_canon_facts", []),
                "summary": new_summary,
                "facts_added": len(new_canon) - len(canon)
            },
            "error": None
        }

    except Exception as e:
        return {
            "status": "ok",
            "data": {
                "db": db,
                "new_facts": [],
                "summary": summary,
                "_warning": str(e)
            },
            "error": None
        }


MEMORY_TOOLS = [npc_memory_tool]