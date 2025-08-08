from fastapi import FastAPI
from .routes import router

app = FastAPI()
app.include_router(router)

def run():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)
