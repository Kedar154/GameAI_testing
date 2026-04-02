from nodes.gamestate import State
from nodes.database_1 import retrieve
from nodes.llms import speed
import json


def retrieval(state: State):
    npc_name = state["current_npc"]
    npc      = state["npcs"][npc_name]
    chat_hist = npc.chat_history or []

    if not chat_hist:
        return {"npcs": {**state["npcs"], npc_name: npc}}

    message          = chat_hist[-1].get("player", "")
    answer_from_db   = retrieve(message)
    npc.retrieved_data = answer_from_db if isinstance(answer_from_db, str) else str(answer_from_db)

    return {"npcs": {**state["npcs"], npc_name: npc}}


def detect_lie(state: State):
    npc_name = state["current_npc"]
    npc      = state["npcs"][npc_name]
    chat_hist = npc.chat_history or []

    if not chat_hist:
        return {"npcs": {**state["npcs"], npc_name: npc}}

    last_message = chat_hist[-1]
    if "player" not in last_message:
        return {"npcs": {**state["npcs"], npc_name: npc}}

    player_message = last_message["player"]
    lies_told      = npc.lies_told   or []
    lies_caught    = npc.lies_caught or []
    evidence_found = state.get("evidence_found", [])

    # Only run if there are lies to catch
    if not lies_told:
        return {"npcs": {**state["npcs"], npc_name: npc}}

    prompt = f"""You are a lie detection system for a murder mystery game.
Respond in JSON only. No explanation. No extra text.

PLAYER MESSAGE: {player_message}

LIES THE NPC HAS TOLD: {lies_told}

LIES ALREADY CAUGHT: {lies_caught}

EVIDENCE THE PLAYER HAS FOUND: {evidence_found}

TASK: Determine if the player's message catches any of the NPC's lies.
A lie is caught ONLY if the player directly references evidence that contradicts it.
Do NOT invent lies.

OUTPUT — respond with this exact JSON:
{{"caught": "exact words of the lie if caught, or none"}}"""

    try:
        raw      = speed.invoke(prompt).content   # ← .content fixes the AIMessage bug
        start    = raw.find("{")
        end      = raw.rfind("}") + 1
        ans      = json.loads(raw[start:end])
        caught   = ans.get("caught", "none")

        if caught and caught.lower() != "none":
            if caught not in lies_caught:
                lies_caught.append(caught)
                npc.lies_caught = lies_caught
                print(f"[detect_lie] Caught lie: {caught}")

    except Exception as e:
        print(f"[detect_lie] failed: {e}")

    return {"npcs": {**state["npcs"], npc_name: npc}}


print("retrieval_lie_detection.py: run successful")