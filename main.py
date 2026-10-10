from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import os
import time
import json
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

app = FastAPI(title="OpenReview.AI")
templates = Jinja2Templates(directory="templates")
ai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class PRSubmission(BaseModel):
    author: str
    title: str
    diff: str

def submit_to_hedera_hcs(message: str) -> dict:
    """Submits a permanent record to the Hedera Consensus Service."""
    operator_id = os.getenv("HEDERA_OPERATOR_ID")
    operator_key = os.getenv("HEDERA_OPERATOR_KEY")
    topic_id = os.getenv("HEDERA_TOPIC_ID")
    
    # Graceful fallback if Hedera testnet keys are missing
    if not all([operator_id, operator_key, topic_id]):
        return {
            "receipt": f"MOCK-TX-{int(time.time())} (Keys missing)",
            "url": None
        }
        
    try:
        from hiero_sdk_python.client.client import Client
        from hiero_sdk_python.crypto.private_key import PrivateKey
        from hiero_sdk_python.consensus.topic_message_submit_transaction import TopicMessageSubmitTransaction
        
        client = Client.for_testnet()
        client.set_operator(operator_id, PrivateKey.from_string(operator_key))
        
        transaction = TopicMessageSubmitTransaction()
        transaction.topic_id = topic_id
        transaction.message = message.encode('utf-8')
        tx_response = transaction.execute(client)
        
        tx_id_str = str(tx_response.transaction_id).replace('@', '-').replace('.', '-')
        return {
            "receipt": str(tx_response.transaction_id),
            "url": f"https://hashscan.io/testnet/transaction/{tx_id_str}"
        }
    except Exception as e:
        return {"receipt": f"Error: {str(e)}", "url": None}

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.post("/api/review")
async def process_pull_request(pr: PRSubmission):
    # 1. Generate AI Code Review
    try:
        response = ai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert AI code reviewer. Analyze the code diff and provide a concise, actionable review summarizing bugs, security issues, or improvements."},
                {"role": "user", "content": f"Title: {pr.title}\n\nDiff:\n{pr.diff}"}
            ]
        )
        ai_review = response.choices[0].message.content
    except Exception as e:
        ai_review = f"AI Error: {str(e)}"

    # 2. Log Verification to Hedera HCS
    hcs_payload = json.dumps({
        "event": "PR_REVIEWED",
        "author": pr.author,
        "title": pr.title,
        "status": "Verified by OpenReview.AI"
    })
    hedera_result = submit_to_hedera_hcs(hcs_payload)

    return {
        "ai_review": ai_review,
        "hedera_receipt": hedera_result["receipt"],
        "tx_url": hedera_result["url"]
    }