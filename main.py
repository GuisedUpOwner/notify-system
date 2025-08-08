from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
from notifier import send_push_notification

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
