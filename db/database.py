import sqlite3

con = sqlite3.connect("AI_story.db", check_same_thread=False)
cur = con.cursor()
