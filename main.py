from nodes.gamestate import State
from nodes.retrieval_lie_detection import retrieval, detect_lie
from nodes.llms import speed, conv
from nodes.summarizer import summarization_node
from nodes.interaction import prompt_repsonse
from nodes.input_node import input_node
from nodes.sus import sus
from nodes.intent import intent

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt
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

garph = StateGraph(State)
garph.add_node('retrieve', retrieval)
garph.add_node('lie_detection', detect_lie)
garph.add_node('sus', sus)
garph.add_node('prompt_response', prompt_repsonse)
garph.add_node('summary', summarization_node)
garph.add_node('input', input_node)
garph.add_node('intent', intent)

garph.set_entry_point("input")

garph.add_edge("input",   "intent")
garph.add_conditional_edges()
garph.add_edge("retrieval",        "lie_detection")
garph.add_edge('lie_detection', "sus")
garph.add_edge("sus",    "prompt_response")
garph.add_edge("prompt_response", "summarize")
garph.add_edge("summarize",        "input")
