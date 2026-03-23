import requests
import json
from langchain_core.tools import tool

# HF_API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"
# HF_TOKEN = "hf_api_key" #yet to place

# def call_hf_llm(prompt: str) -> str:
#     headers = {"Authorization": f"Bearer {HF_TOKEN}"}
#     payload = {
#         "inputs": prompt,
#         "parameters": {
#             "max_new_tokens": 200,
#             "return_full_text": False
#         }
#     }
#     response = requests.post(HF_API_URL, headers=headers, json=payload)
#     result = response.json()
    
#     if isinstance(result, list):
#         return result[0]["generated_text"].strip()
#     return ""


@tool
def detect_lie(
    player_message: str,
    lies_told: str,        # JSON string from state["npc_states"][npc_id]["lies_told"]
    lies_caught: str,      # JSON string from state["npc_states"][npc_id]["lies_caught"]
    evidence_found: str,   # JSON string from state["evidence_found"]
) -> str:
    """Detect if the player has caught an NPC in a lie.
    Call this after every converse_npc call.
    lies_told: pass npc_states[npc_id]['lies_told'] as JSON string.
    lies_caught: pass npc_states[npc_id]['lies_caught'] as JSON string.
    evidence_found: pass the evidence_found list as JSON string."""

    prompt = f"""<s>[INST]
You are a lie detection system for a murder mystery game. 
Respond in JSON only. No explanation. No extra text.

PLAYER MESSAGE:
{player_message}

LIES THE NPC HAS TOLD:
{json.dumps(lies_told, indent=2)}

LIES ALREADY CAUGHT:
{lies_caught}

EVIDENCE THE PLAYER HAS FOUND:
{evidence_found}

TASK:
Determine if the player's message has caught or challenged any of the NPC's lies.
A lie is caught if the player references evidence or information that directly contradicts it.

Respond with exactly this JSON structure:
{{
  "lie_caught": true or false,
  "topic": "the key from lies_told that was caught, or null",
  "reason": "one sentence explanation"
}}
[/INST]"""

    raw = speed.invoke(prompt)

    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        return raw[start:end]   # return JSON string — tool must return string
    except Exception:
        return json.dumps({"lie_caught": False, "topic": None, "reason": "parse error"})
    
