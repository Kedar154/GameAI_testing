from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import interrupt, Command
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import TypedDict, Annotated
import json
import os

api = os.environ["GOOGLE_API_KEY"]

# ── State ─────────────────────────────────────────────────────────────────────

class GameState(TypedDict):
    messages: Annotated[list, add_messages]
    player_score: int
    items_found: list

# ── LLM ──────────────────────────────────────────────────────────────────────

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", google_api_key = api)

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
    score = state["player_score"]
    items = state["items_found"]

    system_prompt = f"""You are a game assistant.

CURRENT GAME STATE:
- Player score: {score}
- Items found: {items}

When calling give_reward, you MUST pass player_score={score} as an argument.
Respond conversationally after tool results."""

    response = llm_with_tools.invoke(
        [SystemMessage(content=system_prompt)] + state["messages"]
    )
    return {"messages": [response]}


def update_state_node(state: GameState):
    # find last tool message
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

    new_score = state["player_score"] + data["bonus"]
    new_items = state["items_found"] + [data["item_name"]]

    print(f"\n[STATE UPDATED] score: {state['player_score']} → {new_score}")
    print(f"[STATE UPDATED] items: {state['items_found']} → {new_items}")

    return {
        "player_score": new_score,
        "items_found": new_items
    }


def human_input_node(state: GameState):
    # graph pauses here every time, waiting for next player message
    player_input = interrupt("Waiting for player input")
    return {"messages": [HumanMessage(content=player_input)]}

# ── Routing ───────────────────────────────────────────────────────────────────

def after_agent(state: GameState):
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "human_input"

# ── Graph wiring ──────────────────────────────────────────────────────────────

checkpointer = MemorySaver()
graph = StateGraph(GameState)

graph.add_node("agent", agent_node)
graph.add_node("tools", ToolNode(tools))
graph.add_node("update_state", update_state_node)
graph.add_node("human_input", human_input_node)

graph.add_edge(START, "agent")
graph.add_conditional_edges("agent", after_agent)
graph.add_edge("tools", "update_state")
graph.add_edge("update_state", "agent")
graph.add_edge("human_input", "agent")

app = graph.compile(checkpointer=checkpointer)

# ── Run ───────────────────────────────────────────────────────────────────────

config = {"configurable": {"thread_id": "session_1"}}

# first message — pass full initial state
result = app.invoke({
    "messages": [HumanMessage(content="hello, what can you do?")],
    "player_score": 75,
    "items_found": ["rusty_key"]
}, config=config)

print("\nAssistant:", result["messages"][-1].content)
print("Score:", result["player_score"])
print("Items:", result["items_found"])

# conversation loop
while True:
    player_input = input("\nYou: ")
    if player_input.lower() == "exit":
        break

    result = app.invoke(
        Command(resume=player_input),
        config=config
    )

    print("\nAssistant:", result["messages"][-1].content)
    print("Score:", result["player_score"])
    print("Items:", result["items_found"])