from groq import Groq

client = Groq(api_key="YOUR_GROQ_API_KEY")

SUMMARY_PROMPT = """You are summarizing one NPC interaction from a detective game.

Write exactly ONE sentence (max 20 words) that captures the most useful investigative signal from this exchange.

Focus on:
- what the NPC denied, avoided, or revealed
- what topic made them nervous or defensive
- what clue or accusation came up
- any contradiction or suspicious reaction

Do NOT write emotional fluff.
Do NOT start with "The player".
Be direct and factual.
Return only the summary sentence.

Examples:
"Bell denied poisoning Thorne but became defensive when aconite was mentioned."
"Arjun appeared anxious when page 42 was brought up."
"Mrs. Graves stayed calm and redirected questions about the pantry."

NPC: {npc_name}
Player said: {player_input}
NPC replied: {npc_response}
"""


def summarization_node(state: State, npc_name: str, player_input: str, npc_response: str):
    prompt = SUMMARY_PROMPT.format(
        npc_name=npc_name,
        player_input=player_input,
        npc_response=npc_response
    )

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=40
    )

    summary_line = response.choices[0].message.content.strip().split("\n")[0]

    if state["officer"].summary:
        state["officer"].summary += " " + summary_line
    else:
        state["officer"].summary = summary_line

    return state