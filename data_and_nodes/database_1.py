from dotenv import load_dotenv
import os
load_dotenv()

google_key = os.getenv("GEMINI_API_KEY2")



import json
import re
import os
import google.genai as genai


INTENT_CATALOG = {
    "inspect_evidence":         "Player wants to examine or learn about a specific piece of evidence",
    "interrogate_npc":          "Player wants to question or learn about a specific NPC suspect or character",
    "explore_location":         "Player wants to explore or get information about a location in the library",
    "check_timeline":           "Player asks about the timeline, sequence of events, or what happened at a specific time",
    "find_connections":         "Player asks what links two things — evidence to NPC, NPC to location, etc.",
    "check_alibi":              "Player asks about a character's alibi or whereabouts claim",
    "check_motive":             "Player asks about why someone would commit the murder — motive",
    "check_facts":              "Player asks to verify or review established facts from the investigation",
    "get_phase_status":         "Player asks about investigation phase progress or what to investigate next",
    "accuse_suspect":           "Player wants to formally accuse a character of the murder",
    "list_suspects":            "Player wants to know who the suspects are",
    "list_evidence":            "Player wants to know all evidence or what has been discovered",
    "list_locations":           "Player wants to know what locations exist or are accessible",
    "check_relationships":      "Player asks about the relationship between two specific characters",
    "get_npc_mental_state":     "Player asks about a character's current emotional or mental state",
    "check_win_condition":      "Player asks what is needed to solve the case or make a final accusation",
    "get_global_state":         "Player asks about the setting — storm, escape routes, telegraph lines",
    "unknown":                  "Intent could not be determined from the query",
}

ENTITY_TYPES = {
    "npc":       ["Arjun Singh", "Dr. Arthur Bell", "Mrs. Eleanor Graves", "Elias Thorne"],
    "evidence":  ["Brandy Glass", "Ledger", "Pantry Log", "Botanical Crates",
                  "Torn Page 42", "Visha Vigyan Manuscript", "Stopped Clock"],
    "location":  ["Study", "Storage Room", "Kitchen Annex", "Reading Hall", "Archive Hall"],
}

SYSTEM_PROMPT = f"""
You are the intent detection engine for a 1920s colonial murder mystery game called "The Shimla Ledger".
The player is investigating the murder of Elias Thorne at the Viceregal Library, Shimla, 1926.

SUSPECTS: Arjun Singh, Dr. Arthur Bell, Mrs. Eleanor Graves
VICTIM: Elias Thorne
EVIDENCE: Brandy Glass, Ledger, Pantry Log, Botanical Crates, Torn Page 42, Visha Vigyan Manuscript, Stopped Clock
LOCATIONS: Study, Storage Room, Kitchen Annex, Reading Hall, Archive Hall

Your job is to analyse the player input and return a JSON object with exactly these fields:

{{
  "intent": "<one of the intent keys listed below>",
  "entities": {{
    "npc": "<NPC full name if mentioned, else null>",
    "npc_2": "<second NPC full name if two NPCs are mentioned, else null>",
    "evidence": "<evidence item name if mentioned, else null>",
    "location": "<location name if mentioned, else null>",
    "time": "<time string if mentioned e.g. 7:15 PM, else null>"
  }},
  "confidence": <float between 0.0 and 1.0>,
  "reasoning": "<one sentence explaining why you chose this intent>"
}}

INTENT KEYS AND MEANINGS:
{json.dumps(INTENT_CATALOG, indent=2)}

ENTITY MATCHING RULES:
- Match NPC names loosely: "Graves", "the steward", "Eleanor" -> "Mrs. Eleanor Graves"
- Match evidence loosely: "the brandy", "the glass" -> "Brandy Glass"; "the book" or "poison manual" -> "Visha Vigyan Manuscript"
- Match locations loosely: "the kitchen", "pantry" -> "Kitchen Annex"; "the archive" -> "Archive Hall"
- If two NPCs are mentioned, fill both npc and npc_2

RESPONSE FORMAT:
- Return ONLY the raw JSON object
- No markdown, no explanation, no code fences
- All keys must be present even if null
"""


class IntentEngine:
    """
    Uses Google Gemini to classify player input into a structured intent
    with extracted entities. Falls back gracefully on API or parse errors.
    """

    def __init__(self, api_key: str):
        google_key = api_key
        genai.configure(api_key=api_key)

        self._model = genai.GenerativeModel(
            model_name="gemini-3-flash-preview",
            system_instruction=SYSTEM_PROMPT,
        )
        print("[Gemini] Intent engine ready.")

    def detect_intent(self, player_input: str) -> dict | None:
        """
        Send player input to Gemini and parse the structured intent response.
        Returns a dict with keys: intent, entities, confidence, reasoning.
        Returns None if parsing fails.
        """
        raw_text = ""
        try:
            response = self._model.generate_content(player_input)
            raw_text = response.text.strip()

            raw_text = re.sub(r"^```(?:json)?", "", raw_text).strip()
            raw_text = re.sub(r"```$",           "", raw_text).strip()

            parsed = json.loads(raw_text)
            return parsed

        except json.JSONDecodeError as e:
            print(f"[Gemini] JSON parse error: {e}")
            print(f"[Gemini] Raw response: {raw_text[:200]}")
            return None
        except Exception as e:
            print(f"[Gemini] API error: {e}")
            return None





"""
QueryBuilder — maps every intent to a parameterised Cypher query.

Each handler returns (cypher_string, params_dict).
Returns (None, {}) when the intent cannot be resolved (missing required entity, etc.)
"""


class QueryBuilder:

    def build(self, intent: str, entities: dict) -> tuple[str | None, dict]:
        handler = self._handlers.get(intent)
        if not handler:
            return None, {}
        return handler(self, entities)



    def _inspect_evidence(self, entities: dict):
        evidence = entities.get("evidence")
        if not evidence:

            cypher = """
                MATCH (e:Evidence)
                OPTIONAL MATCH (e)-[:LOCATED_IN]->(l:Location)
                RETURN e.name AS name,
                       e.phase AS phase,
                       e.reveals AS reveals,
                       e.sensory_detail AS sensory_detail,
                       e.significance AS significance,
                       l.name AS location
                ORDER BY e.phase
            """
            return cypher, {}

        cypher = """
            MATCH (e:Evidence {name: $evidence})
            OPTIONAL MATCH (e)-[:LOCATED_IN]->(l:Location)
            OPTIONAL MATCH (e)-[:LINKS_TO]->(n:NPC)
            OPTIONAL MATCH (e)-[:PROVES]->(f:Fact)
            RETURN e.name AS name,
                   e.phase AS phase,
                   e.reveals AS reveals,
                   e.sensory_detail AS sensory_detail,
                   e.significance AS significance,
                   e.state AS state,
                   l.name AS location,
                   collect(DISTINCT n.name) AS linked_npcs,
                   collect(DISTINCT f.name) AS proven_facts
        """
        return cypher, {"evidence": evidence}

    def _interrogate_npc(self, entities: dict):
        npc = entities.get("npc")
        if not npc:
            return None, {}

        cypher = """
            MATCH (n:NPC {name: $npc})
            OPTIONAL MATCH (n)-[:WAS_AT]->(l:Location)
            OPTIONAL MATCH (n)-[:CLAIMS]->(alibi:Fact)
            OPTIONAL MATCH (n)-[:BELIEVES]->(belief:Fact)
            OPTIONAL MATCH (n)-[:SUSPECTS]->(suspect:NPC)
            OPTIONAL MATCH (n)-[:STARTS_AS]->(ms:MentalState)
            RETURN n.name AS name,
                   n.role AS role,
                   n.personality AS personality,
                   n.state AS state,
                   n.alignment AS alignment,
                   n.lie AS lie,
                   n.dialogue_constraints AS dialogue_constraints,
                   n.red_herring_weight AS red_herring_weight,
                   n.movements_tonight AS movements_tonight,
                   collect(DISTINCT l.name) AS known_locations,
                   collect(DISTINCT alibi.name) AS alibi_claims,
                   collect(DISTINCT belief.name) AS beliefs,
                   collect(DISTINCT suspect.name) AS suspects_list,
                   ms.name AS mental_state
        """
        return cypher, {"npc": npc}

    def _explore_location(self, entities: dict):
        location = entities.get("location")
        if not location:
            cypher = """
                MATCH (l:Location)
                RETURN l.name AS name, l.full_name AS full_name,
                       l.floor AS floor, l.wing AS wing
                ORDER BY l.floor DESC
            """
            return cypher, {}

        cypher = """
            MATCH (l:Location {name: $location})
            OPTIONAL MATCH (e:Evidence)-[:LOCATED_IN]->(l)
            OPTIONAL MATCH (n:NPC)-[:WAS_AT]->(l)
            OPTIONAL MATCH (ev:Event)-[:OCCURRED_AT]->(l)
            RETURN l.name AS name,
                   l.full_name AS full_name,
                   l.floor AS floor,
                   l.wing AS wing,
                   l.lighting AS lighting,
                   l.sound AS sound,
                   l.architecture AS architecture,
                   l.clue_chair AS clue_chair,
                   l.clue_decanter AS clue_decanter,
                   l.clue_frost AS clue_frost,
                   l.clue_carpet AS clue_carpet,
                   l.clue_smell AS clue_smell,
                   l.clue_tray AS clue_tray,
                   l.clue_monkshood AS clue_monkshood,
                   l.clue_vial AS clue_vial,
                   l.clue_crates AS clue_crates,
                   l.clue_notes AS clue_notes,
                   l.clue_folders AS clue_folders,
                   l.interaction_window AS interaction_window,
                   l.interaction_fireplace AS interaction_fireplace,
                   l.interaction_bookshelves AS interaction_bookshelves,
                   collect(DISTINCT e.name) AS evidence_here,
                   collect(DISTINCT n.name) AS npcs_here,
                   collect(DISTINCT ev.desc + ' (' + ev.time + ')') AS events_here
        """
        return cypher, {"location": location}

    def _check_timeline(self, entities: dict):
        time_val = entities.get("time")
        if time_val:
            cypher = """
                MATCH (ev:Event {time: $time})
                OPTIONAL MATCH (ev)-[:OCCURRED_AT]->(l:Location)
                OPTIONAL MATCH (n:NPC)-[:INVOLVED_IN]->(ev)
                RETURN ev.time AS time,
                       ev.desc AS description,
                       l.name AS location,
                       collect(DISTINCT n.name) AS npcs_involved
            """
            return cypher, {"time": time_val}

        cypher = """
            MATCH (ev:Event)
            OPTIONAL MATCH (ev)-[:OCCURRED_AT]->(l:Location)
            OPTIONAL MATCH (n:NPC)-[:INVOLVED_IN]->(ev)
            RETURN ev.time AS time,
                   ev.desc AS description,
                   l.name AS location,
                   collect(DISTINCT n.name) AS npcs_involved
            ORDER BY ev.time
        """
        return cypher, {}

    def _find_connections(self, entities: dict):
        npc      = entities.get("npc")
        evidence = entities.get("evidence")
        location = entities.get("location")
        npc_2    = entities.get("npc_2")

        if npc and evidence:
            cypher = """
                MATCH (e:Evidence {name: $evidence})
                MATCH (n:NPC {name: $npc})
                OPTIONAL MATCH (e)-[r1:LINKS_TO]->(n)
                OPTIONAL MATCH (e)-[r2:ACCESSED_BY]->(n)
                OPTIONAL MATCH (e)-[r3:PROVES]->(f:Fact)
                OPTIONAL MATCH (n)-[:RESPONSIBLE_FOR]->(f2:Fact)
                RETURN e.name AS evidence,
                       n.name AS npc,
                       type(r1) AS link_type,
                       r1.role AS link_role,
                       collect(DISTINCT f.name) AS evidence_proves,
                       collect(DISTINCT f2.name) AS npc_responsible_for
            """
            return cypher, {"evidence": evidence, "npc": npc}

        if npc and location:
            cypher = """
                MATCH (n:NPC {name: $npc})
                MATCH (l:Location {name: $location})
                OPTIONAL MATCH (n)-[r:WAS_AT]->(l)
                OPTIONAL MATCH (ev:Event)-[:OCCURRED_AT]->(l)
                OPTIONAL MATCH (n)-[:INVOLVED_IN]->(ev)
                RETURN n.name AS npc,
                       l.name AS location,
                       r.time AS npc_was_here_at,
                       collect(DISTINCT ev.desc + ' (' + ev.time + ')') AS events_in_location
            """
            return cypher, {"npc": npc, "location": location}

        if npc and npc_2:
            cypher = """
                MATCH (a:NPC {name: $npc}), (b:NPC {name: $npc_2})
                OPTIONAL MATCH (a)-[r1]->(b)
                OPTIONAL MATCH (b)-[r2]->(a)
                RETURN a.name AS npc_a,
                       b.name AS npc_b,
                       collect(DISTINCT type(r1)) AS a_to_b_relations,
                       collect(DISTINCT type(r2)) AS b_to_a_relations
            """
            return cypher, {"npc": npc, "npc_2": npc_2}

        if npc:
            cypher = """
                MATCH (n:NPC {name: $npc})
                OPTIONAL MATCH (e:Evidence)-[:LINKS_TO]->(n)
                OPTIONAL MATCH (n)-[:WAS_AT]->(l:Location)
                OPTIONAL MATCH (n)-[:INVOLVED_IN]->(ev:Event)
                RETURN n.name AS npc,
                       collect(DISTINCT e.name) AS linked_evidence,
                       collect(DISTINCT l.name) AS visited_locations,
                       collect(DISTINCT ev.desc + ' (' + ev.time + ')') AS events
            """
            return cypher, {"npc": npc}

        return None, {}

    def _check_alibi(self, entities: dict):
        npc = entities.get("npc")
        if not npc:
            cypher = """
                MATCH (n:NPC)-[:CLAIMS]->(f:Fact {is_lie: true})
                RETURN n.name AS npc, f.name AS alibi_claim, n.lie AS detailed_lie
            """
            return cypher, {}

        cypher = """
            MATCH (n:NPC {name: $npc})
            OPTIONAL MATCH (n)-[:CLAIMS]->(alibi:Fact)
            OPTIONAL MATCH (n)-[:WAS_AT]->(l:Location)
            OPTIONAL MATCH (n)-[:LIES]->(lie:Fact)
            RETURN n.name AS npc,
                   n.lie AS stated_lie,
                   n.movements_tonight AS actual_movements,
                   collect(DISTINCT alibi.name) AS alibi_claims,
                   collect(DISTINCT {location: l.name, time: n.movements_tonight}) AS actual_locations,
                   collect(DISTINCT lie.name) AS contradicted_facts
        """
        return cypher, {"npc": npc}

    def _check_motive(self, entities: dict):
        npc = entities.get("npc")
        if not npc:
            cypher = """
                MATCH (n:NPC)
                WHERE n.motive IS NOT NULL OR n.innocence = false
                OPTIONAL MATCH (n)-[:RESPONSIBLE_FOR]->(f:Fact)
                RETURN n.name AS npc,
                       n.motive AS motive,
                       n.guilt_status AS guilt_status,
                       collect(DISTINCT f.name) AS responsible_for
            """
            return cypher, {}

        cypher = """
            MATCH (n:NPC {name: $npc})
            OPTIONAL MATCH (n)-[:DISCOVERED_SECRET_OF|CONFRONTED]-(v:NPC)
            OPTIONAL MATCH (n)-[:RESPONSIBLE_FOR]->(f:Fact)
            RETURN n.name AS npc,
                   n.motive AS motive,
                   n.guilt_status AS guilt_status,
                   n.secret AS secret,
                   collect(DISTINCT v.name) AS connected_to_victim,
                   collect(DISTINCT f.name) AS responsible_for
        """
        return cypher, {"npc": npc}

    def _check_facts(self, entities: dict):
        cypher = """
            MATCH (f:Fact)
            OPTIONAL MATCH (e:Evidence)-[:PROVES]->(f)
            RETURN f.name AS fact,
                   f.type AS fact_type,
                   f.is_lie AS is_lie,
                   collect(DISTINCT e.name) AS proven_by
            ORDER BY f.type
        """
        return cypher, {}

    def _get_phase_status(self, entities: dict):
        cypher = """
            MATCH (p:Phase)
            OPTIONAL MATCH (p)-[:TRIGGERED_BY]->(e:Evidence)
            OPTIONAL MATCH (p)-[:UNLOCKS]->(ue:Evidence)
            OPTIONAL MATCH (p)-[:LEADS_TO]->(next:Phase)
            OPTIONAL MATCH (p)-[:BREAKS]->(n:NPC)
            RETURN p.name AS phase,
                   p.phase_number AS number,
                   p.trigger_action AS trigger,
                   p.discovery AS discovery,
                   p.outcome AS outcome,
                   collect(DISTINCT e.name) AS triggered_by_evidence,
                   collect(DISTINCT ue.name) AS unlocks_evidence,
                   next.name AS leads_to_phase,
                   n.name AS breaks_npc
            ORDER BY p.phase_number
        """
        return cypher, {}

    def _accuse_suspect(self, entities: dict):
        npc = entities.get("npc")
        if not npc:
            return None, {}

        cypher = """
            MATCH (w:WinCondition)
            MATCH (target:NPC {name: w.accusation_target})
            OPTIONAL MATCH (w)-[:REQUIRES]->(req:Evidence)
            OPTIONAL MATCH (w)-[:FALSE_TARGET]->(false_t:NPC)
            RETURN w.accusation_target AS correct_target,
                   $npc AS accused_by_player,
                   (w.accusation_target = $npc) AS is_correct,
                   w.condition_description AS condition,
                   w.false_accusation_outcome AS false_outcome,
                   collect(DISTINCT req.name) AS required_evidence,
                   collect(DISTINCT false_t.name) AS false_targets
        """
        return cypher, {"npc": npc}

    def _list_suspects(self, entities: dict):
        cypher = """
            MATCH (n:NPC)
            WHERE n.is_victim IS NULL OR n.is_victim = false
            OPTIONAL MATCH (n)-[:STARTS_AS]->(ms:MentalState)
            RETURN n.name AS name,
                   n.role AS role,
                   n.state AS state,
                   n.red_herring_weight AS red_herring_weight,
                   n.innocence AS is_innocent,
                   ms.name AS mental_state
            ORDER BY n.name
        """
        return cypher, {}

    def _list_evidence(self, entities: dict):
        cypher = """
            MATCH (e:Evidence)
            OPTIONAL MATCH (e)-[:LOCATED_IN]->(l:Location)
            RETURN e.name AS name,
                   e.phase AS phase,
                   e.significance AS significance,
                   l.name AS location
            ORDER BY e.phase, e.name
        """
        return cypher, {}

    def _list_locations(self, entities: dict):
        cypher = """
            MATCH (l:Location)
            OPTIONAL MATCH (e:Evidence)-[:LOCATED_IN]->(l)
            RETURN l.name AS name,
                   l.full_name AS full_name,
                   l.floor AS floor,
                   l.wing AS wing,
                   collect(DISTINCT e.name) AS evidence_available
            ORDER BY l.floor DESC, l.name
        """
        return cypher, {}

    def _check_relationships(self, entities: dict):
        npc   = entities.get("npc")
        npc_2 = entities.get("npc_2")
        if not npc or not npc_2:
            if npc:
                cypher = """
                    MATCH (n:NPC {name: $npc})-[r]-(other:NPC)
                    RETURN n.name AS from_npc,
                           type(r) AS relationship,
                           other.name AS to_npc
                """
                return cypher, {"npc": npc}
            return None, {}

        cypher = """
            MATCH (a:NPC {name: $npc}), (b:NPC {name: $npc_2})
            OPTIONAL MATCH (a)-[r1]->(b)
            OPTIONAL MATCH (b)-[r2]->(a)
            OPTIONAL MATCH (a)-[:DISCOVERED_SECRET_OF]->(b)
            RETURN a.name AS npc_a,
                   b.name AS npc_b,
                   collect(DISTINCT type(r1)) AS a_to_b,
                   collect(DISTINCT type(r2)) AS b_to_a
        """
        return cypher, {"npc": npc, "npc_2": npc_2}

    def _get_npc_mental_state(self, entities: dict):
        npc = entities.get("npc")
        if not npc:
            cypher = """
                MATCH (n:NPC)-[:STARTS_AS]->(ms:MentalState)
                WHERE n.is_victim IS NULL OR n.is_victim = false
                OPTIONAL MATCH (n)-[:TRANSITIONS_TO]->(breakdown:MentalState {name: "Breakdown"})
                RETURN n.name AS npc,
                       ms.name AS current_state,
                       n.mental_shock_trigger AS shock_trigger
            """
            return cypher, {}

        cypher = """
            MATCH (n:NPC {name: $npc})-[:STARTS_AS]->(ms:MentalState)
            OPTIONAL MATCH (n)-[:TRANSITIONS_TO {trigger: n.mental_shock_trigger}]->(breakdown:MentalState)
            OPTIONAL MATCH (n)-[:BREAKS_DOWN_WHEN]->(e:Evidence)
            RETURN n.name AS npc,
                   ms.name AS initial_state,
                   n.mental_shock_trigger AS shock_trigger,
                   n.shock_confession AS confession_content,
                   collect(DISTINCT e.name) AS breakdown_evidence
        """
        return cypher, {"npc": npc}

    def _check_win_condition(self, entities: dict):
        cypher = """
            MATCH (w:WinCondition)
            OPTIONAL MATCH (w)-[:REQUIRES]->(req:Evidence)
            OPTIONAL MATCH (w)-[:TARGETS]->(target:NPC)
            OPTIONAL MATCH (w)-[:FALSE_TARGET]->(false_t:NPC)
            RETURN w.accusation_target AS target,
                   w.condition_description AS condition,
                   w.false_accusation_outcome AS false_accusation_outcome,
                   collect(DISTINCT req.name) AS required_evidence,
                   collect(DISTINCT false_t.name) AS false_targets
        """
        return cypher, {}

    def _get_global_state(self, entities: dict):
        cypher = """
            MATCH (g:GlobalState)
            MATCH (s:StoryMetadata)
            RETURN s.title AS title,
                   s.setting AS setting,
                   s.year AS year,
                   s.atmosphere AS atmosphere,
                   g.storm_intensity AS storm_intensity,
                   g.telegraph_lines AS telegraph_lines,
                   g.roads_passable AS roads_passable,
                   g.escape_possible AS escape_possible,
                   g.current_officer_hint AS officer_hint
        """
        return cypher, {}

    def _unknown(self, entities: dict):
        return None, {}


    _handlers = {
        "inspect_evidence":     _inspect_evidence,
        "interrogate_npc":      _interrogate_npc,
        "explore_location":     _explore_location,
        "check_timeline":       _check_timeline,
        "find_connections":     _find_connections,
        "check_alibi":          _check_alibi,
        "check_motive":         _check_motive,
        "check_facts":          _check_facts,
        "get_phase_status":     _get_phase_status,
        "accuse_suspect":       _accuse_suspect,
        "list_suspects":        _list_suspects,
        "list_evidence":        _list_evidence,
        "list_locations":       _list_locations,
        "check_relationships":  _check_relationships,
        "get_npc_mental_state": _get_npc_mental_state,
        "check_win_condition":  _check_win_condition,
        "get_global_state":     _get_global_state,
        "unknown":              _unknown,
    }
    
    
from neo4j import GraphDatabase


class Neo4jClient:
    """
    Thin wrapper around the Neo4j Python driver.
    Handles connection, session management, and query execution.
    """

    def __init__(self, config: dict):
        uri      = config["uri"]
        username = config["username"]
        password = config["password"]

        self._driver = GraphDatabase.driver(uri, auth=(username, password))


        try:
            self._driver.verify_connectivity()
            print(f"[Neo4j] Connected to {uri}")
        except Exception as e:
            raise ConnectionError(f"[Neo4j] Could not connect: {e}")

    def run(self, query: str, params: dict = None) -> list:
        """
        Execute a Cypher query and return all records as a list of dicts.
        Returns an empty list on error rather than crashing the game loop.
        """
        params = params or {}
        try:
            with self._driver.session() as session:
                result  = session.run(query, params)
                records = [dict(record) for record in result]
                return records
        except Exception as e:
            print(f"[Neo4j] Query error: {e}")
            return []

    def close(self):
        self._driver.close()
        print("[Neo4j] Connection closed.")
        
        



"""
ResponseFormatter — converts raw Neo4j records into
atmospheric, in-character Game Master narrative text.
"""


class ResponseFormatter:

    def format(self, intent: str, entities: dict, records: list, original_input: str) -> str:
        if not records:
            return self._no_data(entities)

        handler = self._handlers.get(intent, self._generic)
        return handler(self, records, entities, original_input)



    def _fmt_inspect_evidence(self, records, entities, _):
        if len(records) > 1:

            lines = ["Here is what has been catalogued so far:\n"]
            for r in records:
                lines.append(f"  • {r['name']} (Phase {r['phase']}) — found in {r.get('location', 'unknown location')}")
                if r.get("reveals"):
                    lines.append(f"    Reveals: {r['reveals']}")
            return "\n".join(lines)

        r = records[0]
        parts = []
        if r.get("sensory_detail"):
            parts.append(r["sensory_detail"])
        if r.get("reveals"):
            parts.append(f"Upon closer examination: {r['reveals']}")
        if r.get("significance"):
            parts.append(f"Significance: {r['significance']}")
        if r.get("location"):
            parts.append(f"Found in: {r['location']}")
        if r.get("linked_npcs") and any(r["linked_npcs"]):
            parts.append(f"This connects to: {', '.join(r['linked_npcs'])}")
        if r.get("proven_facts") and any(r["proven_facts"]):
            parts.append(f"This proves: {', '.join(r['proven_facts'])}")
        return "\n".join(parts) if parts else f"The {r['name']} sits before you, silent."

    def _fmt_interrogate_npc(self, records, entities, _):
        r = records[0]
        parts = [f"{r['name']} — {r.get('role', 'Unknown role')}"]
        parts.append(f"Demeanour: {r.get('personality', 'Difficult to read')}")
        if r.get("mental_state"):
            parts.append(f"Current state: {r['mental_state']}")
        if r.get("movements_tonight"):
            parts.append(f"Tonight's movements: {r['movements_tonight']}")
        if r.get("alibi_claims") and any(r["alibi_claims"]):
            parts.append(f"Claims: {'; '.join(r['alibi_claims'])}")
        if r.get("suspects_list") and any(r["suspects_list"]):
            parts.append(f"Suspects: {', '.join(r['suspects_list'])}")
        if r.get("dialogue_constraints"):
            parts.append(f"Note: {r['dialogue_constraints']}")
        return "\n".join(parts)

    def _fmt_explore_location(self, records, entities, _):
        if len(records) > 1:
            lines = ["The accessible locations within the library:\n"]
            for r in records:
                evidence_str = ", ".join(r["evidence_available"]) if r.get("evidence_available") and any(r["evidence_available"]) else "none yet"
                lines.append(f"  • {r['full_name'] or r['name']} (Floor {r['floor']}, {r.get('wing','?')} Wing)")
                lines.append(f"    Evidence here: {evidence_str}")
            return "\n".join(lines)

        r = records[0]
        parts = [f"You enter the {r.get('full_name') or r['name']}."]
        if r.get("lighting"):
            parts.append(r["lighting"])
        if r.get("sound"):
            parts.append(r["sound"])
        if r.get("architecture"):
            parts.append(r["architecture"])

        clues = [
            r.get("clue_chair"), r.get("clue_decanter"), r.get("clue_frost"),
            r.get("clue_carpet"), r.get("clue_smell"), r.get("clue_tray"),
            r.get("clue_monkshood"), r.get("clue_vial"), r.get("clue_crates"),
            r.get("clue_notes"), r.get("clue_folders"),
        ]
        clues = [c for c in clues if c]
        if clues:
            parts.append("\nYou observe the following:")
            for c in clues:
                parts.append(f"  — {c}")

        if r.get("evidence_here") and any(r["evidence_here"]):
            parts.append(f"\nEvidence present: {', '.join(r['evidence_here'])}")
        if r.get("npcs_here") and any(r["npcs_here"]):
            parts.append(f"Others present: {', '.join(r['npcs_here'])}")
        if r.get("events_here") and any(r["events_here"]):
            parts.append(f"Events recorded here: {'; '.join(r['events_here'])}")

        return "\n".join(parts)

    def _fmt_check_timeline(self, records, entities, _):
        if len(records) == 1:
            r = records[0]
            loc_str = f" at {r['location']}" if r.get("location") else ""
            npc_str = f" — {', '.join(r['npcs_involved'])} involved" if r.get("npcs_involved") and any(r["npcs_involved"]) else ""
            return f"{r['time']}{loc_str}: {r['description']}{npc_str}"

        lines = ["The verified timeline of this evening's events:\n"]
        for r in records:
            loc_str = f" [{r['location']}]" if r.get("location") else ""
            npc_str = f" ({', '.join(r['npcs_involved'])})" if r.get("npcs_involved") and any(r["npcs_involved"]) else ""
            lines.append(f"  {r['time']}{loc_str} — {r['description']}{npc_str}")
        return "\n".join(lines)

    def _fmt_find_connections(self, records, entities, _):
        r = records[0]
        parts = []
        if r.get("evidence") and r.get("npc"):
            role = r.get("link_role") or r.get("link_type") or "connected"
            parts.append(f"Connection between {r['evidence']} and {r['npc']}: {role}")
            if r.get("evidence_proves") and any(r["evidence_proves"]):
                parts.append(f"The evidence proves: {', '.join(r['evidence_proves'])}")
        elif r.get("npc") and r.get("location"):
            time = r.get("npc_was_here_at") or "at some point tonight"
            parts.append(f"{r['npc']} was at {r['location']} — {time}")
            if r.get("events_in_location") and any(r["events_in_location"]):
                parts.append(f"Events recorded there: {'; '.join(r['events_in_location'])}")
        elif r.get("npc_a") and r.get("npc_b"):
            parts.append(f"Relationship between {r['npc_a']} and {r['npc_b']}:")
            if r.get("a_to_b_relations") and any(r["a_to_b_relations"]):
                parts.append(f"  {r['npc_a']} → {r['npc_b']}: {', '.join(r['a_to_b_relations'])}")
            if r.get("b_to_a_relations") and any(r["b_to_a_relations"]):
                parts.append(f"  {r['npc_b']} → {r['npc_a']}: {', '.join(r['b_to_a_relations'])}")
        elif r.get("npc"):
            parts.append(f"Connections for {r['npc']}:")
            if r.get("linked_evidence") and any(r["linked_evidence"]):
                parts.append(f"  Evidence: {', '.join(r['linked_evidence'])}")
            if r.get("visited_locations") and any(r["visited_locations"]):
                parts.append(f"  Locations visited: {', '.join(r['visited_locations'])}")
        return "\n".join(parts) if parts else "No connection found."

    def _fmt_check_alibi(self, records, entities, _):
        if len(records) > 1:
            lines = ["Alibi statements on record:\n"]
            for r in records:
                lines.append(f"  • {r['npc']}: \"{r['alibi_claim']}\"")
                if r.get("detailed_lie"):
                    lines.append(f"    Full claim: {r['detailed_lie']}")
            return "\n".join(lines)

        r = records[0]
        parts = [f"Alibi for {r['npc']}:"]
        if r.get("stated_lie"):
            parts.append(f"  Claims: {r['stated_lie']}")
        if r.get("actual_movements"):
            parts.append(f"  Actual movements: {r['actual_movements']}")
        if r.get("contradicted_facts") and any(r["contradicted_facts"]):
            parts.append(f"  This contradicts: {', '.join(r['contradicted_facts'])}")
        return "\n".join(parts)

    def _fmt_check_motive(self, records, entities, _):
        parts = []
        for r in records:
            parts.append(f"{r['npc']}:")
            if r.get("motive"):
                parts.append(f"  Motive: {r['motive']}")
            elif r.get("guilt_status") == "Killer":
                parts.append("  Motive: Concealment of financial embezzlement.")
            else:
                parts.append("  No confirmed motive for murder.")
            if r.get("secret"):
                parts.append(f"  Hidden secret: {r['secret']}")
        return "\n".join(parts)

    def _fmt_check_facts(self, records, entities, _):
        truths = [r for r in records if not r.get("is_lie")]
        lies   = [r for r in records if r.get("is_lie")]
        lines  = ["Established facts of the investigation:\n"]
        for r in truths:
            proven = f" (proven by: {', '.join(r['proven_by'])})" if r.get("proven_by") and any(r["proven_by"]) else ""
            lines.append(f"  ✓ {r['fact']}{proven}")
        if lies:
            lines.append("\nKnown false alibi claims:")
            for r in lies:
                lines.append(f"  ✗ {r['fact']}")
        return "\n".join(lines)

    def _fmt_get_phase_status(self, records, entities, _):
        lines = ["Investigation phase breakdown:\n"]
        for r in records:
            lines.append(f"Phase {r['number']}: {r['phase']}")
            lines.append(f"  Trigger: {r['trigger']}")
            lines.append(f"  Discovery: {r['discovery']}")
            lines.append(f"  Outcome: {r['outcome']}")
            if r.get("leads_to_phase"):
                lines.append(f"  Leads to: {r['leads_to_phase']}")
            if r.get("breaks_npc"):
                lines.append(f"  Breaks: {r['breaks_npc']}")
            lines.append("")
        return "\n".join(lines)

    def _fmt_accuse_suspect(self, records, entities, _):
        r = records[0]
        accused  = r.get("accused_by_player", "Unknown")
        correct  = r.get("is_correct", False)
        required = r.get("required_evidence", [])

        if correct:
            return (
                f"You accuse {accused}.\n"
                "A silence falls over the room. The evidence is irrefutable.\n"
                "Mrs. Eleanor Graves exhales slowly.\n"
                "\"So you have uncovered the truth.\"\n"
                "\"Twenty years I kept this library running. Twenty winters. Twenty budgets.\"\n"
                "\"And that man would have destroyed everything over numbers in a ledger.\"\n"
                "\"I only meant to frighten him. But the poison worked faster than I expected.\"\n\n"
                "THE CASE IS SOLVED."
            )
        else:
            req_str = ", ".join(required) if required else "the key evidence"
            return (
                f"You accuse {accused}. But their alibi holds.\n"
                f"{r.get('false_accusation_outcome', 'The investigation resets.')}\n"
                f"Hint: Gather {req_str} before making your final accusation."
            )

    def _fmt_list_suspects(self, records, entities, _):
        lines = ["The suspects present in the library tonight:\n"]
        for r in records:
            if r.get("is_victim"):
                continue
            rh = r.get("red_herring_weight") or "Unknown"
            lines.append(f"  • {r['name']} — {r.get('role','?')}")
            lines.append(f"    State: {r.get('state','?')} | Suspicion weight: {rh}")
        return "\n".join(lines)

    def _fmt_list_evidence(self, records, entities, _):
        by_phase = {}
        for r in records:
            ph = r.get("phase", 0)
            by_phase.setdefault(ph, []).append(r)

        lines = ["Evidence catalogue:\n"]
        for ph in sorted(by_phase):
            lines.append(f"Phase {ph}:")
            for r in by_phase[ph]:
                loc = r.get("location") or "unknown"
                lines.append(f"  • {r['name']} — {loc}")
                if r.get("significance"):
                    lines.append(f"    {r['significance']}")
        return "\n".join(lines)

    def _fmt_list_locations(self, records, entities, _):
        lines = ["Accessible areas of the Viceregal Library:\n"]
        for r in records:
            ev = ", ".join(r["evidence_available"]) if r.get("evidence_available") and any(r["evidence_available"]) else "none catalogued"
            lines.append(f"  • {r['full_name'] or r['name']} (Floor {r['floor']}, {r.get('wing','?')} Wing)")
            lines.append(f"    Evidence: {ev}")
        return "\n".join(lines)

    def _fmt_check_relationships(self, records, entities, _):
        r = records[0]
        parts = []
        if r.get("npc_a") and r.get("npc_b"):
            parts.append(f"Relationship — {r['npc_a']} ↔ {r['npc_b']}:")
            if r.get("a_to_b") and any(r["a_to_b"]):
                parts.append(f"  {r['npc_a']} → {r['npc_b']}: {', '.join(r['a_to_b'])}")
            if r.get("b_to_a") and any(r["b_to_a"]):
                parts.append(f"  {r['npc_b']} → {r['npc_a']}: {', '.join(r['b_to_a'])}")
        else:
            for rec in records:
                parts.append(f"  {rec.get('from_npc')} —[{rec.get('relationship')}]→ {rec.get('to_npc')}")
        return "\n".join(parts) if parts else "No relationships found."

    def _fmt_get_npc_mental_state(self, records, entities, _):
        if len(records) > 1:
            lines = ["Mental states of the suspects:\n"]
            for r in records:
                lines.append(f"  • {r['npc']}: {r.get('current_state','?')}")
                if r.get("shock_trigger"):
                    lines.append(f"    Breaks when: {r['shock_trigger']}")
            return "\n".join(lines)

        r = records[0]
        parts = [f"{r['npc']} is currently {r.get('initial_state','composed')}."]
        if r.get("shock_trigger"):
            parts.append(f"They will break when: {r['shock_trigger']}")
        if r.get("confession_content"):
            parts.append(f"Confession: {r['confession_content']}")
        if r.get("breakdown_evidence") and any(r["breakdown_evidence"]):
            parts.append(f"Evidence needed: {', '.join(r['breakdown_evidence'])}")
        return "\n".join(parts)

    def _fmt_check_win_condition(self, records, entities, _):
        r = records[0]
        req = ", ".join(r["required_evidence"]) if r.get("required_evidence") else "unknown"
        false_t = ", ".join(r["false_targets"]) if r.get("false_targets") else "none"
        return (
            f"To solve the case you must:\n"
            f"  1. Gather all required evidence: {req}\n"
            f"  2. Present them during the final confrontation with: {r.get('target','?')}\n\n"
            f"False accusation targets (will fail): {false_t}\n"
            f"If you accuse incorrectly: {r.get('false_accusation_outcome','Investigation resets.')}"
        )

    def _fmt_get_global_state(self, records, entities, _):
        r = records[0]
        escape = "No" if not r.get("escape_possible") else "Yes"
        roads  = "Impassable" if not r.get("roads_passable") else "Clear"
        return (
            f"{r.get('title','The Shimla Ledger')} — {r.get('setting','?')}, {r.get('year','?')}\n"
            f"Atmosphere: {r.get('atmosphere','?')}\n"
            f"Storm intensity: {r.get('storm_intensity','?')}\n"
            f"Telegraph lines: {r.get('telegraph_lines','?')}\n"
            f"Roads: {roads} | Escape possible: {escape}\n"
            f"Officer's note: \"{r.get('officer_hint','')}\""
        )

    def _generic(self, records, entities, _):
        if not records:
            return self._no_data(entities)
        r = records[0]
        return "\n".join(f"{k}: {v}" for k, v in r.items() if v is not None)

    @staticmethod
    def _no_data(entities):
        entity_str = next((v for v in entities.values() if v), None)
        if entity_str:
            return f"No records found for '{entity_str}'. It may not yet be part of the investigation."
        return "No information found. Try asking about a suspect, evidence item, or location."


    _handlers = {
        "inspect_evidence":     _fmt_inspect_evidence,
        "interrogate_npc":      _fmt_interrogate_npc,
        "explore_location":     _fmt_explore_location,
        "check_timeline":       _fmt_check_timeline,
        "find_connections":     _fmt_find_connections,
        "check_alibi":          _fmt_check_alibi,
        "check_motive":         _fmt_check_motive,
        "check_facts":          _fmt_check_facts,
        "get_phase_status":     _fmt_get_phase_status,
        "accuse_suspect":       _fmt_accuse_suspect,
        "list_suspects":        _fmt_list_suspects,
        "list_evidence":        _fmt_list_evidence,
        "list_locations":       _fmt_list_locations,
        "check_relationships":  _fmt_check_relationships,
        "get_npc_mental_state": _fmt_get_npc_mental_state,
        "check_win_condition":  _fmt_check_win_condition,
        "get_global_state":     _fmt_get_global_state,
    }






def run_game_query(
    player_input: str,
    neo4j_client,
    intent_engine,
    query_builder,
    response_formatter
):


    intent_data = intent_engine.detect_intent(player_input)

    if not intent_data:
        return "The officer pauses. \"I couldn't interpret that.\""

    intent   = intent_data.get("intent", "unknown")
    entities = intent_data.get("entities", {})




    cypher, params = query_builder.build(intent, entities)

    if not cypher:
        return "The question lacks clarity. Try specifying a suspect, evidence, or location."




    records = neo4j_client.run(cypher, params)




    response = response_formatter.format(
        intent=intent,
        entities=entities,
        records=records,
        original_input=player_input
    )

    return response




# Neo4j
neo4j_client = Neo4jClient({
    "uri": "neo4j+s://1cf51ba7.databases.neo4j.io",
    "username": "1cf51ba7",
    "password": "ZZbPhtj6cw6VeITHbcYwIcZ1s3bu6JeosoghY8_HDfs"
})


intent_engine = IntentEngine(api_key=google_key)


query_builder = QueryBuilder()


response_formatter = ResponseFormatter()



def retrieve(user_input):
    user_input = input("\nPlayer: ")

    output = run_game_query(
        user_input,
        neo4j_client,
        intent_engine,
        query_builder,
        response_formatter
    )

    out = ("\nDatabase:\n", output)
    return out