from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import TypedDict, Annotated
import json

# ── State ────────────────────────────────────────────────────────────────────

class GameState(TypedDict):
    messages: Annotated[list, add_messages]
    player_score: int        # we will use this inside a tool
    items_found: list

# ── LLM ──────────────────────────────────────────────────────────────────────

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite")

# ── Tools ─────────────────────────────────────────────────────────────────────

@tool
def get_weather(city: str) -> str:
    """Get the weather for a city."""
    return f"Weather in {city} is sunny."


@tool
def search_item(item_name: str) -> str:
    """Search for an item in the game world."""
    return json.dumps({
        "item": item_name,
        "found": True,
        "description": f"{item_name} is a rare artifact."
    })


@tool
def give_reward(item_name: str, player_score: int) -> str:
    """Give the player a reward based on their current score.
    player_score: pass the current score from game state."""

    # ── this tool uses a state variable passed as argument ────────────
    if player_score > 50:
        bonus = 100
        message = f"High scorer bonus! You get {item_name} + 100 points."
    else:
        bonus = 20
        message = f"Standard reward. You get {item_name} + 20 points."

    return json.dumps({
        "item_name": item_name,
        "bonus": bonus,
        "message": message
    })

tools = [get_weather, search_item, give_reward]
llm_with_tools = llm.bind_tools(tools)

# ── Nodes ─────────────────────────────────────────────────────────────────────

def agent_node(state: GameState):
    # ── node has full state access ────────────────────────────────────
    score = state["player_score"]
    items = state["items_found"]

    system_prompt = f"""You are a game assistant.

CURRENT GAME STATE:
- Player score: {score}
- Items found: {items}

When calling give_reward, you MUST pass player_score={score} as an argument.
"""
    response = llm_with_tools.invoke(
        [SystemMessage(content=system_prompt)] + state["messages"]
    )
    return {"messages": [response]}


def update_state_node(state: GameState):
    # ── runs after every tool call, updates state from tool result ────
    last_tool_msg = None
    for msg in reversed(state["messages"]):
        if isinstance(msg, ToolMessage):
            last_tool_msg = msg
            break

    if not last_tool_msg:
        return {}

    # only process give_reward results
    try:
        data = json.loads(last_tool_msg.content)
    except Exception:
        return {}

    if "bonus" not in data:
        return {}

    # update state fields
    new_score = state["player_score"] + data["bonus"]
    new_items = state["items_found"] + [data["item_name"]]

    return {
        "player_score": new_score,
        "items_found": new_items
    }

# ── Graph wiring ──────────────────────────────────────────────────────────────

checkpointer = MemorySaver()
graph = StateGraph(GameState)

graph.add_node("agent", agent_node)
graph.add_node("tools", ToolNode(tools))
graph.add_node("update_state", update_state_node)

graph.add_edge(START, "agent")
graph.add_conditional_edges("agent", tools_condition)
graph.add_edge("tools", "update_state")
graph.add_edge("update_state", "agent")

app = graph.compile(checkpointer=checkpointer)

# ── Run ───────────────────────────────────────────────────────────────────────

config = {"configurable": {"thread_id": "test_session_1"}}

initial_state = {
    "messages": [HumanMessage(content="give me a reward for finding the golden sword")],
    "player_score": 75,
    "items_found": ["rusty_key"]
}

result = app.invoke(initial_state, config=config)

print("Final score:", result["player_score"])
print("Items found:", result["items_found"])
print("Last message:", result["messages"][-1].content)



'''
**The three places state is accessed — summarised clearly:**
```
agent_node(state)        → reads state directly, injects into system prompt
                           so LLM knows current score and passes it to tool

give_reward(player_score) → receives state value as argument
                            cannot read state itself, Officer LLM passes it

update_state_node(state) → reads state directly, reads ToolMessage result,
                           returns dict → LangGraph merges back into state
'''