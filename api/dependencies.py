import sqlite3
from fastapi import HTTPException


def get_db():
    # Return error code 500 if connection fails
    try:
        con = sqlite3.connect("AI_story.db", check_same_thread=False)
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {e}")
    try:
        yield con
    finally:
        con.close()
