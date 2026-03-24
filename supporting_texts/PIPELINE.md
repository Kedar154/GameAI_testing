```
class NPCState(TypedDict):
    emotion:        str        # composed | defensive | pre_breakdown | breakdown
    sus_score:      int        # 0–100
    lies_told:      Dict       # {"lie_key": "exact text NPC said"} — built dynamically
    lies_caught:    List[str]  # lie keys already caught — never recheck
    chat_history:   List[Dict] # this NPC's turns only {"role": "player"|"npc", "text": str}
    short_term:     List[str]  # raw last N turns for memory compression
    turn_count:     int        # resets after compress_short_term_memory fires

class GameState(TypedDict):
    session_id:           str
    player_id:            str
    player_input:         str
    active_npc:           str        # "arjun" | "bell" | "graves"
    case_file:            List[str]  # evidence IDs discovered so far
    total_turns:          int        # sum across all NPCs
    total_sus:            int        # graves_sus + arjun_sus + bell_sus
    investigation_score:  float      # total_sus + (total_turns × 0.5)
    accusation_ready:     bool       # True when all 3 key evidence in case_file
    npc_states:           Dict[str, NPCState]
    npc_db:               Dict       # summarizer memory — canon + summaries
```

---

### The Pipeline — Every Turn
```
PLAYER INPUT RECEIVED
        │
        ▼
══════════════════════════════════════════
STEP 1 — RELEVANCY CHECK
  tool:     check_relevancy (groq, embedding or llm method)
  input:    player_input, last 2 turns from npc_states[active_npc]["chat_history"]
  output:   relevant: bool, score: float
  if not relevant:
      → return deflection message ("The officer looks puzzled...")
      → do NOT update any state
      → END turn
══════════════════════════════════════════
        │ relevant = True
        ▼
══════════════════════════════════════════
STEP 2 — LIE DETECTION
  tool:     detect_lie (groq)
  input:    player_input
            npc_states[active_npc]["lies_told"]   (what NPC has said so far)
            npc_states[active_npc]["lies_caught"]  (skip these)
            case_file                              (evidence player has)
  output:   lie_caught: bool, topic: str|None, reason: str
  if lie_caught:
      → append topic to npc_states[active_npc]["lies_caught"]
══════════════════════════════════════════
        │
        ▼
══════════════════════════════════════════
STEP 3 — UPDATE SUS SCORE  (pure function, no LLM)
  function: update_sus_score()
  input:    current npc_states[active_npc]["sus_score"]
            lie_caught (from step 2)
            topic (lie key, for increment lookup)
            active_npc
  logic:
      if lie_caught:
          increment = SUS_INCREMENTS[active_npc][topic]  ← from config dict
          new_score = min(100, current + increment)
  output:   updated sus_score → write to npc_states[active_npc]["sus_score"]
  then:
      recalculate total_sus = sum of all 3 npc sus_scores
      recalculate investigation_score = total_sus + (total_turns × 0.5)
      write both back to GameState
══════════════════════════════════════════
        │
        ▼
══════════════════════════════════════════
STEP 4 — UPDATE NPC EMOTION  (pure function, no LLM)
  function: update_npc_emotion()
  input:    active_npc, sus_score, case_file, accusation_ready
  logic:
      GRAVES:
          if sus_score >= 95 and accusation_ready: → "breakdown"
          elif sus_score >= 75:                    → "pre_breakdown"
          elif sus_score >= 25:                    → "defensive"
          else:                                    → "composed"
      ARJUN:
          if sus_score >= 28:   → "breakdown"
          elif sus_score >= 16: → "defensive"
          else:                 → "composed"
      BELL:
          if sus_score >= 25:   → "breakdown"
          elif sus_score >= 15: → "defensive"
          else:                 → "composed"
  output:   updated emotion → write to npc_states[active_npc]["emotion"]

  SPECIAL: if Bell hits breakdown for first time:
      → add bells_testimony to case_file (+25 to graves_sus)
      → recalculate total_sus and investigation_score
      → re-run update_npc_emotion() for graves with new sus_score
══════════════════════════════════════════
        │
        ▼
══════════════════════════════════════════
STEP 5 — CHECK ACCUSATION READY  (pure function)
  function: check_accusation_ready()
  input:    case_file
  logic:
      required = {"coal_ledger", "empty_aconite_vial", "pantry_service_log"}
      accusation_ready = required.issubset(set(case_file))
  output:   write accusation_ready to GameState
══════════════════════════════════════════
        │
        ▼
══════════════════════════════════════════
STEP 6 — FETCH NPC MEMORY
  tool:     get_npc_memory (summarizer_tool.py)
  input:    npc_id=active_npc, payload={"db": state["npc_db"]}
  output:   canon_facts: List[str], summary: dict
            (behavior, topics_discussed, key_context)
  used in:  building the system prompt for Gemini
══════════════════════════════════════════
        │
        ▼
══════════════════════════════════════════
STEP 7 — FETCH NPC DATA FROM NEO4J
  function: get_npc_data() (database_thing.ipynb, cloud Neo4j)
  input:    npc_id → mapped to full name ("graves" → "Mrs. Eleanor Graves")
  output:   personality, truth, lie (base lie, not the dynamic ones),
            npc_emotion (current state from DB — we override with state emotion)
  note:     emotion from state always wins over DB value
══════════════════════════════════════════
        │
        ▼
══════════════════════════════════════════
STEP 8 — CACHE LOOKUP
  tool:     manage_cache (operation="lookup")
  input:    MD5 hash of (npc_id + player_input + emotion + case_file sorted)
            session_id + player_id used as namespace prefix on cache key
  output:   hit: bool, response: str|None
  if hit:
      → skip steps 9 and 10
      → go directly to step 11
══════════════════════════════════════════
        │ cache miss
        ▼
══════════════════════════════════════════
STEP 9 — BUILD SYSTEM PROMPT
  function: build_npc_prompt() (pure function)
  inputs:
      npc_data        (from step 7)
      emotion         (from step 4)
      canon_facts     (from step 6)
      summary         (from step 6)
      case_file       (global)
      lies_told       (npc_states[active_npc]["lies_told"])
      lies_caught     (npc_states[active_npc]["lies_caught"])
      chat_history    (last 6 turns from npc_states[active_npc]["chat_history"])

  prompt structure:
      IDENTITY:       who the NPC is, their role, 1926 Shimla setting
      PERSONALITY:    from Neo4j
      TRUTH:          hidden — never reveal unless breakdown
      BASE LIE:       from Neo4j — their cover story
      EMOTION:        current state + behavior instructions per state
      CANON FACTS:    what has already been established — never contradict these
      SUMMARY:        recent behavior, topics discussed, key context
      EVIDENCE KNOWN: what evidence the player has presented
      DYNAMIC LIES:   lies_told so far — stay consistent, never contradict
      LIES CAUGHT:    these have been exposed — admit partially, don't re-lie
      RULES:
          - Max 2 sentences
          - Stay in character
          - If you lie, record it (see step 10b)
          - Never contradict canon_facts or lies_told
══════════════════════════════════════════
        │
        ▼
══════════════════════════════════════════
STEP 10 — GEMINI NPC RESPONSE
  model:    Gemini (conv)
  input:    system prompt (step 9) + player_input
  output:   npc_response: str

  10a — EXTRACT AND RECORD LIES (groq, fast)
      After Gemini responds, run a quick groq call:
      "Did the NPC just tell a new lie in this response?
       If yes, return {lie_key: str, lie_text: str}, else null"
      if new lie detected:
          → add to npc_states[active_npc]["lies_told"][lie_key] = lie_text

  10b — STORE IN CACHE
      tool: manage_cache (operation="store")
      key:  same hash as step 8
      value: npc_response
══════════════════════════════════════════
        │
        ▼
══════════════════════════════════════════
STEP 11 — UPDATE CHAT HISTORY AND TURN COUNT
  function: pure state update
  actions:
      append to npc_states[active_npc]["chat_history"]:
          {"role": "player", "text": player_input}
          {"role": "npc",    "text": npc_response}
      append to npc_states[active_npc]["short_term"]:
          f"Player: {player_input}"
          f"NPC: {npc_response}"
      increment npc_states[active_npc]["turn_count"] by 1
      increment state["total_turns"] by 1
      recalculate investigation_score
══════════════════════════════════════════
        │
        ▼
══════════════════════════════════════════
STEP 12 — MEMORY COMPRESSION (conditional)
  condition: npc_states[active_npc]["turn_count"] >= 8
  tool:      compress_short_term_memory
  input:     npc_id, payload={
                 "short_term":       npc_states[active_npc]["short_term"],
                 "previous_summary": npc_db[active_npc]["summary"]
             }
  output:    updated_summary, clear_short_term=True, reset_turn_count=True
  actions:
      → update npc_db[active_npc]["summary"] with updated_summary
      → clear npc_states[active_npc]["short_term"] = []
      → reset npc_states[active_npc]["turn_count"] = 0

  condition: end of NPC conversation (player switches NPC or session ends)
  tool:      process_npc_memory → then update_npc_db
  input:     latest_conversation (full short_term),
             canon_facts (npc_db[active_npc]["canon"]),
             previous_summary (npc_db[active_npc]["summary"])
  output:    new_canon_facts, updated_summary
  actions:
      → call update_npc_db to persist new canon + summary into npc_db
══════════════════════════════════════════
        │
        ▼
RETURN npc_response TO PLAYER
```

---

### Evidence Discovery Pipeline (separate from NPC turns)
```
PLAYER CLICKS "SEARCH LOCATION"
        │
        ▼
STEP A — CHECK LOCATION GATE (pure function)
  input:    location, total_sus, case_file, npc sus scores
  logic:
      storage_room:  total_sus > 15 AND "brandy_glass" in case_file
      admin_office:  total_sus > 50 AND arjun_sus > 20
      pantry:        total_sus > 90 AND bell_sus > 20
      others:        always open
  if gate not met:
      → return "The officer shakes his head. Not yet."
      → END

STEP B — RETURN SCRIPTED EVIDENCE TEXT (pure DB read, no LLM)
  input:    location, case_file (to know what's already found)
  output:   list of new evidence items found at this location
            each with: evidence_id, officer_script (from Neo4j)
  for each new evidence item:
      → add evidence_id to case_file
      → add sus_score weight to appropriate NPC sus_score
      → recalculate total_sus and investigation_score
      → re-run update_npc_emotion() for affected NPC
      → re-run check_accusation_ready()
      → display officer_script to player