from nodes.gamestate import State
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
def run(command):
    for _ in graph.stream(command, config=config):
        pass
    return graph.get_state(config).tasks[0].interrupts[0].value

inp = input("You: ")
print("NPC:", run({"player_input": inp, "npc_response": "Good evening."}))

# Game loop
while True:
    player_input = input("You: ")
    if player_input == "quit":
        break
    print("NPC:", run(Command(resume=player_input)))