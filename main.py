from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict

from requests import Session
from db import get_db
from notifier import send_push_notification
from usecases.phase_change import process_phase_change

app = FastAPI()

class NotificationRequest(BaseModel):
    tokens: List[str]
    title: str
    body: str
    image: Optional[str] = None
    data: Optional[Dict[str, str]] = None

@app.post("/send-notifications")
def send_notification(req: NotificationRequest):
    result = send_push_notification(
        tokens=req.tokens,
        title=req.title,
        body=req.body,
        image=req.image,
        data=req.data
    )

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))

    return result



@app.post("/send-phase-notifications")
async def send_phase_notifications(
    previous_phase_name: str,
    background_tasks: BackgroundTasks,
    user_id: str = None  # replace with your auth layer
):
    background_tasks.add_task(
        process_phase_change,
        user_id=user_id,
        previous_phase=previous_phase_name
    )
    return {"message": "Notifications processing started"}