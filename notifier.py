from typing import List, Optional, Dict
import firebase_admin
from firebase_admin import credentials, messaging
import os

SERVICE_ACCOUNT_PATH = os.path.join(os.getcwd(), 'firebase/hue-social-app-firebase-adminsdk-x72wc-e694a20e99.json')

if not firebase_admin._apps:
    cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
    firebase_admin.initialize_app(cred)

def send_push_notification(
    tokens: List[str],
    title: str,
    body: str,
    image: Optional[str] = None,
    data: Optional[Dict[str, str]] = None
):
    if not tokens:
        return {"success": False, "detail": "No tokens provided"}

    notification = messaging.Notification(title=title, body=body, image=image)

    try:
        if hasattr(messaging, 'send_multicast'):
            message = messaging.MulticastMessage(
                notification=notification,
                tokens=tokens,
                data=data or {}
            )
            result = messaging.send_multicast(message)

            responses = [
                {
                    "token": tokens[i],
                    "success": resp.success,
                    "message_id": getattr(resp, "message_id", None),
                    "exception": str(resp.exception) if resp.exception else None
                }
                for i, resp in enumerate(result.responses)
            ]

            return {
                "success": True,
                "success_count": result.success_count,
                "failure_count": result.failure_count,
                "responses": responses
            }

        else:
            responses = []
            for token in tokens:
                try:
                    message = messaging.Message(
                        notification=notification,
                        token=token,
                        data=data or {}
                    )
                    message_id = messaging.send(message)
                    responses.append({"token": token, "success": True, "message_id": message_id})
                except Exception as e:
                    responses.append({"token": token, "success": False, "error": str(e)})

            return {
                "success": True,
                "success_count": sum(1 for r in responses if r["success"]),
                "failure_count": sum(1 for r in responses if not r["success"]),
                "responses": responses
            }

    except Exception as e:
        return {"success": False, "error": str(e)}
