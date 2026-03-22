import json
import os
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API key check (IMPORTANT)
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("GROQ_API_KEY is not set")

client = Groq(api_key=api_key)


def update_summary(npc_name: str, old_summary: str, question: str, answer: str) -> str:
    prompt = f"""Update this NPC memory state by merging the new interaction.
Output one concise paragraph (max 4 sentences), past tense, third person.

STATE: {old_summary or 'none'}
Q: {question}
A: {answer}
NPC: {npc_name}

Updated state:"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120,
            temperature=0.3
        )

        new_summary = response.choices[0].message.content.strip()

        # Prevent overwriting with empty response
        return new_summary if new_summary else old_summary

    except Exception as e:
        print(f"[ERROR] LLM failed: {e}")
        return old_summary  # fallback


def send_to_db(npc_id: str, npc_name: str, player_id: str, summary: str) -> dict:
    payload = {
        "npc_id": npc_id,
        "npc_name": npc_name,
        "player_id": player_id,
        "summary": summary
    }

    print(json.dumps(payload, indent=2))
    return {"status": "success", "npc_id": npc_id}


def run_session(npc_id: str, npc_name: str, player_id: str, exchanges: list[tuple[str, str]]) -> dict:
    summary = ""

    for question, answer in exchanges:
        summary = update_summary(npc_name, summary, question, answer)

    return send_to_db(npc_id, npc_name, player_id, summary)

