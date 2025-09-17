from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from bot import router as bot_router

app = FastAPI()

origins = ["*"] 


app.add_middleware( 
    CORSMiddleware, 
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(bot_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080)  