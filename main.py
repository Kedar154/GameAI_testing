from nodes.gamestate import State, state
from nodes.retrieval_lie_detection import retrieval, detect_lie
from nodes.llms import speed, conv
from nodes.summarizer import summarization_node
from nodes.interaction import prompt_repsonse
from nodes.input_node import input_node
from nodes.intent import intent
from nodes.graph import garph_ as graph

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command
from langchain_core.tools import tool
#from langchain_core.messages import HumanMessage, SystemMessage
#from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
#from sentence_transformers import SentenceTransformer
from neo4j import GraphDatabase
from typing import TypedDict, Annotated
import numpy as np
import uuid
import os


config = {"configurable": {"thread_id": "session-1"}}
def run(command, first=1):
    for _ in graph.stream(command, config=config):
        pass
    state_values = graph.get_state(config).values
    current_npc = state_values["current_npc"]
    if(current_npc!="search"):
        npc = state_values["npcs"][current_npc]
        #print(current_npc)
        #print(f"npc object: {npc}")          # see full npc state
        #print(f"chat_hist: {npc.chat_history}")
        print(f"retrieved data: {npc.retrieved_data}")
        return f"{state['current_npc']}: {npc.chat_history[-1]["npc"] if npc.chat_history else "could you repeat the question"}"
    else:
        return f"Officer: {state_values["evidence_found"][-1]}"

inp = input("You: ")
run(state, 0)

# Game loop
while True:
    player_input = input("You: ")
    if player_input.lower() in ["quit", "e"]:
        break
    run(Command(resume=player_input))

print("loop ended")