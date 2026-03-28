from groq import Groq

client = Groq(api_key="YOUR_GROQ_API_KEY")

SUMMARY_PROMPT = """You are summarizing one NPC interaction from a detective game.

Write exactly ONE sentence (max 20 words) that captures the most useful investigative signal from this exchange.

Focus on:
- what the NPC denied, avoided, or revealed
- what topic made them nervous or defensive
- what clue or accusation came up
- any contradiction or suspicious reaction

Do NOT write emotional fluff. Do NOT start with "The player". Be direct and factual.

NPC: {npc_name}
Player said: {player_input}
NPC replied: {npc_response}

Write the one-line summary now:"""


def summarization_node(state: State) -> dict:
    npc_name = state["current_npc"]
    player_input = state["player_input"]
    npc_response = state["npc_response"]

    prompt = SUMMARY_PROMPT.format(
        npc_name=npc_name,
        player_input=player_input,
        npc_response=npc_response
    )

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=60
    )

    summary_line = response.choices[0].message.content.strip()

    updated_officer = state["officer"].model_copy(deep=True)

    if updated_officer.summary.strip():
        updated_officer.summary += "\n" + summary_line
    else:
        updated_officer.summary = summary_line

    return {
        "officer": updated_officer
    }
