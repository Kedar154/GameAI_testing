## pip install dotenv
from dotenv import load_dotenv
import os
from langchain_groq import ChatGroq

load_dotenv()
gr1 = os.getenv('GROQ_API1')
gr2 = os.getenv('GROQ_API2')
gr3 = os.getenv('GROQ_API3')

conv = ChatGroq(
    model = "llama-3.3-70b-versatile",
    temperature = 0.2,
    groq_api_key = gr1
)
speed = ChatGroq(
    model = "llama-3.3-70b-versatile",
    temperature = 0,
    groq_api_key = gr3
)

print("llm.py: llms initialised")