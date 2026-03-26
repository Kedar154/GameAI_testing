from groq import Groq

client = Groq(api_key="")


SUMMARY_PROMPT = """You are summarizing one NPC interaction from a detective game.

Write exactly ONE sentence (max 20 words) that captures the most useful investigative signal from this exchange.

Focus on:
- what the NPC denied, avoided, or revealed
- what topic made them nervous or defensive
- what clue or accusation came up
- any contradiction or suspicious reaction

Do NOT write emotional fluff. Do NOT start with "The player". Be direct and factual.

Examples:
"Bell denied poisoning Thorne but became defensive when aconite was mentioned."
"Arjun appeared anxious when page 42 was brought up."
"Mrs. Graves stayed calm and redirected questions about the pantry."

NPC: {npc_name}
Player said: {player_input}
NPC replied: {npc_response}

Write the one-line summary now:"""


def summarization_node(global_state, npc_name, player_input, npc_response):
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

    if "chat_summary" not in global_state:
        global_state["chat_summary"] = []

    global_state["chat_summary"].append(summary_line)

    return global_state