from nodes.gamestate import State, state
from nodes.graph import garph_ as graph
from langgraph.types import Command

config = {"configurable": {"thread_id": "session-1"}}

def run(command):
    for _ in graph.stream(command, config=config):
        pass
    values      = graph.get_state(config).values
    officer_out = values['search_result']
    npc_out     = values.get("npc_response",   "").strip()
    return officer_out if officer_out else (npc_out or "...")

def get_current_npc():
    return graph.get_state(config).values.get("current_npc", "officer")

def show_debug():
    values = graph.get_state(config).values
    print("\n═══ GAME STATE ═══")
    print(f"  current_npc      : {values.get('current_npc')}")
    print(f"  evidence_found   : {values.get('evidence_found')}")
    print(f"  accusation_ready : {values.get('accusation_available')}")
    print(f"  locations:")
    for loc, unlocked in values.get("locations_unlocked", {}).items():
        print(f"    {loc:<22} {'open' if unlocked else 'locked'}")
    print("\n  ── NPC SUS ──")
    for npc_id, npc in values.get("npcs", {}).items():
        print(f"  {npc_id:<8} locations_unlocked={values.get('locations_unlocked',"")} \n evidence_found={values.get('evidence_found', "")}")
        print(f"           summary: {npc.running_summary or '(empty)'}")
        print(f"           retrieved data: {npc.retrieved_data or '(empty)'}")
    print("═══════════════════\n")

print("Type 'quit' to exit. Type 'debug' to see game state.\n")

for _ in graph.stream(state, config=config):
    pass

while True:
    player_input = input("You: ")
    if player_input.lower() == "quit":
        break
    if player_input.lower() == "debug":
        show_debug()
        continue
    response    = run(Command(resume=player_input))
    current_npc = get_current_npc()
    print(f"\n{current_npc}: {response}\n")