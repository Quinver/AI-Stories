import os
from agents import import_agents_from_json
from db import init_db
from api import run
from dotenv import load_dotenv

load_dotenv()

def main():
    print("Initializing database...")
    init_db()
    
    print("Loading agents from JSON...")
    agents = import_agents_from_json()
    print(f"Loaded {len(agents)} agents: {[agent.name for agent in agents]}")

    api_choice = os.environ.get("AI_API", "ollama")
    print(f"Using API: {api_choice}")

    print("\n🌐 Starting web server...")
    print("📱 Open your browser and go to: http://localhost:8081")
    print("🤖 Your AI agents are ready to chat!")
    
    run()

if __name__ == "__main__":
    main()
