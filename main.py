from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import pandas as pd
from llama_index.query_engine import PandasQueryEngine
from llama_index.llms import Ollama
from prompts import new_prompt, instruction_str
from note_engine import note_engine
from llama_index.tools import QueryEngineTool, ToolMetadata
from llama_index.agent import ReActAgent

load_dotenv()

# Load data
agil_path = os.path.join("data", "structured_export.csv")
agil_df = pd.read_csv(agil_path)

# Init LLM
llm = Ollama(
    model="llama3:8b",
    temperature=0.2,
    request_timeout=120
)

# Create query engine
agil_query_engine = PandasQueryEngine(
    df=agil_df,
    verbose=True,
    instruction_str=instruction_str,
    llm=llm
)
agil_query_engine.update_prompts({"pandas": new_prompt})

# Configure tools
tools = [
    note_engine,
    QueryEngineTool(
        query_engine=agil_query_engine,
        metadata=ToolMetadata(
            name="gas_station_data",
            description="Use this tool for queries about gas station locations, coordinates, or attributes.",
        ),
    ),
]

# Create agent
agent = ReActAgent.from_tools(
    tools=tools,
    llm=llm,
    verbose=True,
    max_iterations=7,
    max_output_tokens=1024,
    context="""
    You are a helpful assistant with two capabilities:
    1. Saving notes (use note_saver tool for explicit note requests)
    2. Querying gas station data (use gas_station_data tool for location/coordinate queries)

    Rules:
    - Never use note_saver for data query results
    - For coordinate queries, always use gas_station_data
    - Only use note_saver when explicitly asked to save a note
    """,
    handle_parsing_errors=True
)

# FastAPI setup
app = FastAPI()

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request schema
class PromptRequest(BaseModel):
    prompt: str

# Query processor
def process_query(prompt: str):
    if "save" in prompt.lower() and "note" in prompt.lower():
        return agent.query(prompt)
    else:
        return agil_query_engine.query(prompt)

# Endpoint
@app.post("/chatbot/query")
def chatbot_query(request: PromptRequest):
    try:
        result = process_query(request.prompt)
        return {"response": str(result)}
    except Exception as e:
        return {"response": f"Erreur: {str(e)}"}
