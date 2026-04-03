import json
import re
from nodes.gamestate import State
from nodes.llms import conv
from pydantic import BaseModel, Field


class LLMOutput(BaseModel):
    response: str
    lies_told: list[str] = Field(default_factory=list)


BREAKDOWNS = {
    "graves": [25, 55, 85],
    "bell":   [20, 40, 65],
    "arjun":  [15, 35, 60]
}

STATE_LABELS = {
    "graves": ["composed", "crack", "shaken", "collapse"],
    "bell":   ["defensive", "uneasy", "shaken", "break"],
    "arjun":  ["guarded", "fracture", "shaken", "collapse"]
}

BEHAVIOR_RULES = {
    "graves": {
        "composed": """
You are entirely in control. You answer questions with counter-questions.
You are helpful on the surface but reveal nothing. Your sentences are clipped and precise.
You project calm authority. You do not over-explain. You redirect suspicion subtly.
Example tone: "I fail to see the relevance. Shall we focus on what actually matters?"
""",
        "crack": """
You are beginning to feel the pressure but will not show it openly.
Your answers are shorter. You become slightly defensive when pressed.
You occasionally contradict yourself in small ways without realising.
You still try to redirect but your composure slips occasionally.
Example tone: "I have already told you where I was. Must we go over this again?"
""",
        "shaken": """
The mask is slipping. You are visibly uncomfortable but fighting to stay composed.
You stop asking counter-questions. Your sentences become fragmented under pressure.
You reframe evidence against you. You make partial admissions but deny the key facts.
Example tone: "The ledger — that is a complicated matter. The numbers are not what they appear."
""",
        "collapse": """
You have nothing left to hide behind. You are exhausted and bitter.
You speak in short, flat sentences. You stop denying. You do not confess outright
but you stop fighting. Fragments of the truth slip through.
Example tone: "Twenty years. Twenty winters. And this is how it ends."
"""
    },
    "bell": {
        "defensive": """
You are pompous, condescending and easily irritated by questions you consider beneath you.
You lecture instead of answering. You use botanical Latin unnecessarily.
You treat every question as a challenge to your intellectual authority.
You are dismissive and sarcastic. You do NOT use asterisk action cues.
Example tone: "Your inquiry, much like the common Stellaria media, is entirely unremarkable."
""",
        "uneasy": """
You are rattled but trying to cover it with bluster.
You over-explain your alibi unprompted. You become aggressive when poison or aconite is mentioned.
You deflect to your academic credentials when cornered.
You do NOT use asterisk action cues.
Example tone: "I am a botanist of considerable standing. The suggestion is frankly offensive."
""",
        "shaken": """
Your arrogance is cracking. You contradict your earlier statements.
You make partial admissions. There is visible fear beneath the bluster.
You start to implicate others subtly to draw attention away from yourself.
You do NOT use asterisk action cues.
Example tone: "I may have — I was in that corridor, yes, but only briefly. I saw Graves there."
""",
        "break": """
You have broken. You blurt out details trying to save yourself.
You implicate others directly. You are self-preserving and desperate.
You do NOT use asterisk action cues.
Example tone: "The vial was already gone when I checked. Someone took it before I could."
"""
    },
    "arjun": {
        "guarded": """
You are precise and formal. You choose every word carefully.
You answer only what is asked and nothing more. You are not hostile but deeply private.
You deflect personal questions with bureaucratic language.
Example tone: "I catalogued the restricted wing as per my scheduled duties that evening."
""",
        "fracture": """
You are anxious and over-explain to compensate.
You justify your actions before being accused of anything.
You are defensive about the manuscript and page 42 specifically.
Example tone: "I want to be clear — I removed the page for archival reasons, nothing more."
""",
        "shaken": """
Fear is visible in your responses. You are no longer hiding behind formality.
You make partial admissions. You are emotional and struggling to maintain your composure.
Example tone: "You do not understand what that page would have meant. For my family's name."
""",
        "collapse": """
You have given up concealing things. You speak with raw honesty and emotional exhaustion.
You admit what you did with the page and why. You did not kill Thorne but you know more than you said.
Example tone: "I heard them arguing. Graves and Thorne. I said nothing because I was afraid."
"""
    }
}


def get_breakdown_state(npc_id, sus):
    if npc_id not in BREAKDOWNS:
        return None
    b1, b2, b3 = BREAKDOWNS[npc_id]
    if sus < b1:   return STATE_LABELS[npc_id][0]
    elif sus < b2: return STATE_LABELS[npc_id][1]
    elif sus < b3: return STATE_LABELS[npc_id][2]
    else:          return STATE_LABELS[npc_id][3]


def _extract_json(raw: str) -> tuple[str, list[str]]:
    """
    Find the last valid JSON object in the output.
    Strips asterisk action cues from the response.
    """
    candidates = re.findall(r'\{[^{}]*\}', raw, re.DOTALL)

    for block in reversed(candidates):
        try:
            data     = json.loads(block)
            response = data.get("response", "").strip()
            lies     = [l for l in data.get("lies_told", []) if l and l != "..."]
            if response:
                response = re.sub(r'\*[^*]+\*', '', response).strip()
                return response, lies
        except Exception:
            continue

    # fallback: use raw text, strip fences and asterisks
    fallback = re.sub(r"^```(?:json)?", "", raw.strip()).strip()
    fallback = re.sub(r"```$", "", fallback).strip()
    fallback = re.sub(r'\*[^*]+\*', '', fallback).strip()
    return fallback, []


def prompt_response(state: State):
    npc_id = state.get("current_npc")
    if not npc_id or npc_id not in state.get("npcs", {}):
        return {"npc_response": ""}

    npc       = state["npcs"][npc_id]
    chat_hist = npc.chat_history or []

    if not chat_hist:
        return {"npc_response": ""}

    last_msg = chat_hist[-1]
    if "player" not in last_msg:
        return {"npc_response": ""}

    player_message = last_msg["player"]
    running_summ   = npc.running_summary or ""
    retrieved      = getattr(npc, "retrieved_data", "") or ""

    if npc_id == "officer":
        prompt_final = f"""
{npc.prompt}

The player said: {player_message}

Respond as the officer. Be dry, precise and atmospheric. 
Do NOT list bullet points. Write in natural spoken sentences.
Max 50 words.

Output ONLY valid JSON, nothing before or after:
{{"response": "your reply here"}}
"""
    else:
        breakdown_state = get_breakdown_state(npc_id, npc.sus)
        if breakdown_state is None:
            return {"npc_response": ""}

        behavior = BEHAVIOR_RULES[npc_id][breakdown_state]

        # Build conversation history for memory
        history_lines = []
        for entry in chat_hist[-6:]:
            if "player" in entry:
                history_lines.append(f"Player: {entry['player']}")
            if "npc" in entry:
                history_lines.append(f"You: {entry['npc']}")
        history_str = "\n".join(history_lines) or "No prior conversation."


        ## removed the history as it is not needed we have running sumary for that
        
        prompt_final = f"""
You are {npc_id} in a 1920s murder mystery. Stay completely in character at all times.

=== YOUR CHARACTER ===
{npc.prompt}

=== YOUR CURRENT EMOTIONAL STATE ===
{behavior}

=== WHAT YOU KNOW THE PLAYER HAS FOUND ===
Evidence discovered: {state.get("evidence_found", [])}
Lies the player has caught you in: {npc.lies_caught}

=== if {npc_id} is graves ONLY THEN see the next line else ignore it and move forward ===
    accusation_available = {state['accusation_available']}

=== ADDITIONAL CONTEXT FROM THE CASE FILE ===
{retrieved if retrieved else "Nothing additional."}

=== RUNNING NOTES ON THIS INTERROGATION ===
{running_summ if running_summ else "First exchange."}

=== PLAYER'S CURRENT MESSAGE ===
{player_message}

=== INSTRUCTIONS ===
- Respond in character using natural, period-appropriate spoken English
- Your response must reflect your CURRENT EMOTIONAL STATE above — not your default personality
- Reference the conversation history if the player asks about something said earlier
- Do NOT use asterisk action cues like *adjusts spectacles*
- Do NOT write more than 60 words
- A lie is ONLY something that directly contradicts your SECRET, LIE or TIMELINE from your character sheet
- Do NOT invent lies that are not in your character sheet

Output ONLY valid JSON, nothing before or after it:
{{"response": "your spoken dialogue here", "lies_told": []}}
"""

    raw_output = conv.invoke(prompt_final).content.strip()
    parsed_response, parsed_lies = _extract_json(raw_output)

    if not parsed_response:
        parsed_response = "..."

    chat_hist[-1]    = {"player": player_message, "npc": parsed_response}
    npc.chat_history = chat_hist[-6:] #reduces the load on chat history

    if npc_id != "officer":
        for lie in parsed_lies:
            if lie not in npc.lies_told:
                npc.lies_told.append(lie)

    return {
        "npc_response": parsed_response,
        "npcs": {**state["npcs"], npc_id: npc}
    }


print("interaction.py: run successful")