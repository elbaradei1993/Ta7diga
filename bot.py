from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()

# Replace with your Telegram Admin ID
ADMIN_ID = 123456789  # Change to your real Telegram ID

# Dummy data (replace with real database or bot integration)
active_users = 10
waiting_users = 5
banned_users = set()

class BroadcastMessage(BaseModel):
    message: str

@app.get("/api/stats")
def get_stats():
    return {"active": active_users, "waiting": waiting_users}

@app.post("/api/ban/{user_id}")
def ban_user(user_id: int):
    if user_id in banned_users:
        raise HTTPException(status_code=400, detail="User already banned.")
    banned_users.add(user_id)
    return JSONResponse(content={"message": f"User {user_id} banned."})

@app.post("/api/broadcast")
def broadcast_message(data: BroadcastMessage):
    # Here, connect to your Telegram bot to send messages
    return JSONResponse(content={"message": f"Broadcast sent: {data.message}"})
