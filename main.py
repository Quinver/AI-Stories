import os
from agents import import_agents_from_json, create_agent_conversation
from db import con, init_db
from api import run
from dotenv import load_dotenv
import threading

load_dotenv()


def main():
    init_db()
    agents = import_agents_from_json()

    # Choose API - set this to "openai" to use OpenAI instead of Ollama
    api_choice = os.environ.get("AI_API", "ollama")

    print(f"Using API: {api_choice}")

    # Create a conversation between agents
    with con:
        cur = con.cursor()

        print("\n=== Creating Agent Conversation ===\n")

        conversation_prompt = "A mysterious traveler arrives in town, claiming to know the location of a lost treasure hidden deep in the nearby forest. The townsfolk are skeptical but intrigued. What do you think this traveler wants, and what will you do about it?"

        print(f"Starting conversation with prompt: {conversation_prompt}")
        print("-" * 70)

        create_agent_conversation(
            agents,
            conversation_prompt,
            cur,
            turns=20,
            api=api_choice,
        )




if __name__ == "__main__":
    t1 = threading.Thread(target=main)
    t2 = threading.Thread(target=run)

    t1.start()
    t2.start()

    t1.join()
    t2.join()
