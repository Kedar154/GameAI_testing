from nodes.gamestate import State, state
from nodes.retrieval_lie_detection import retrieval, detect_lie
from nodes.llms import speed, conv
from nodes.summarizer import summarization_node
from nodes.interaction import prompt_repsonse
from nodes.input_node import input_node
from nodes.sus import officer_search_node, discover_evidence_node, accusation_node, update_gates_node
from nodes.intent import intent
from nodes.update_chat import update

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
checkpoint = MemorySaver()
garph = StateGraph(State)
garph.add_node('retrieve', retrieval)
garph.add_node('lie_detection', detect_lie)
garph.add_node('prompt_response', prompt_repsonse)
garph.add_node('summary', summarization_node)
garph.add_node('input', input_node)
##garph.add_node('intent', intent)
garph.add_node("officer_search_node", officer_search_node)
garph.add_node("discover_evidence_node", discover_evidence_node)
garph.add_node("update_gates_node", update_gates_node)
garph.add_node("update", update)

garph.add_node("accusation_node", accusation_node)
garph.set_entry_point("input")
garph.add_edge("input", 'update')
garph.add_conditional_edges(
        "update",
        intent,
        {
            "search": "officer_search_node",
            "npc":       "retrieve",
            "accusation_available":      "accusation_node",
            "officer":         "prompt_response",
        },
    )

garph.add_edge("officer_search_node", "discover_evidence_node")
garph.add_edge("discover_evidence_node", "update_gates_node")
garph.add_edge("update_gates_node",       'input')

garph.add_edge("retrieve",        "lie_detection")
garph.add_edge('lie_detection', "prompt_response")
garph.add_edge("prompt_response", "summary")
garph.add_edge("summary",       'input')

garph.add_edge("accusation_node",       'input')


garph_ = garph.compile(checkpointer=checkpoint)

print("graph compiled")
## connect evidence searching nodes 