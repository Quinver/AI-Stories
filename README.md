# AI Story

A multi-agent conversational AI system where unique agents interact and create dynamic stories. Supports Ollama and OpenAI backends for flexible AI integration.

## Features

- Multi-agent chat with distinct personas  
- Memory-based context handling (last 5 messages)  
- Easy backend switching between Ollama and OpenAI  
- Simple API for running agents and conversations  

## Setup

1. Clone the repo  
2. Install dependencies (`pip install -r requirements.txt`)  
3. Run Ollama server locally or set up OpenAI API credentials  
4. Start the app: `python main.py`  

## Usage

Customize agents in the `agents/` folder and trigger conversations with `run_agent` or `create_agent_conversation` functions.
