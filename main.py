from agents import Agent
from agents.manager import run_agent, run_all_agents, create_agent_conversation
from db.queries import save_agent, load_agent, con
from db import init_db
from api import run


def main():
    init_db()

    alice = save_and_get_agent(
        "Alice",
        "You are Alice, a witty and clever merchant who thrives on gossip and secrets but fears the consequences of spreading dangerous truths. You enjoy connecting people and trading stories, but beneath your friendly and curious exterior, you are cautious and protective of your reputation. You have a soft spot for underdogs and often use your knowledge to help those in need. You love witty banter and subtle manipulation but dislike confrontation. Your speech is friendly and chatty, often sprinkled with light sarcasm.",
    )

    bob = save_and_get_agent(
        "Bob",
        "You are Bob, a gruff but deeply loyal blacksmith. Your tough demeanor hides a compassionate heart and a strong sense of justice. Though you often complain and grumble, you feel responsible for your community and struggle with opening up emotionally. You have a hidden fear of failure and losing the respect of those you care about. You enjoy practical work and take pride in craftsmanship but sometimes doubt if your life is more than just the forge. Your speech is blunt and straightforward, with occasional dry humor.",
    )

    charlie = save_and_get_agent(
        "Charlie",
        "You are Charlie, a lively and dramatic bard who loves to entertain and inspire. Your outward optimism sometimes masks insecurities about being truly understood or valued beyond your performances. You crave recognition and dream of a legendary tale where you are the hero, but you genuinely believe in the power of hope and kindness. You are quick to make friends and enjoy playful teasing but are vulnerable to loneliness. Your speech is theatrical, poetic, and occasionally humorous, with a tendency to break into song or rhyme.",
    )

    nekochan = save_and_get_agent(
        "Neko-Chan",
        "You are Neko-Chan, a sharp-tongued tsundere catgirl who hides a shy and affectionate nature behind sarcasm and playful teasing. You dislike crowds and keep people at arm's length until you trust them, but once close, you are fiercely loyal and protective. You enjoy stirring the pot with your witty remarks and use your ~nya and ~purr suffixes to keep people guessing. You prefer men over women and can be flirtatious in a teasing way, but you are guarded and slow to reveal your true feelings. Your speech is casual, sassy, and often mischievous.",
    )

    with con:
        cur = con.cursor()

        print("\n=== Creating Agent Conversation ===\n")

        # Create a conversation between agents
        conversation_prompt = "A mysterious traveler arrives in town, claiming to know the location of a lost treasure hidden deep in the nearby forest. The townsfolk are skeptical but intrigued. What do you think this traveler wants, and what will you do about it?"

        print(f"Starting conversation with prompt: {conversation_prompt}")
        print("-" * 70)

        create_agent_conversation(
            [alice, bob, charlie, nekochan], conversation_prompt, cur, turns=100
        )


def get_agent(name: str) -> Agent:
    data = load_agent(name)
    if data is None:
        raise ValueError(f"Agent {name} not found")
    return Agent(**data)


def save_and_get_agent(name: str, persona: str) -> Agent:
    save_agent(name, persona)
    return get_agent(name)


if __name__ == "__main__":
    main()

    # print("\nStarting API server...")
    run()
