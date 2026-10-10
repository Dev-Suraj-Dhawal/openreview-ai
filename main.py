from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import os
import time
import json
from dotenv import load_dotenv
from google import genai # Upgraded to the new, supported SDK

# Load environment variables
load_dotenv()

# Initialize the new Gemini client
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

app = FastAPI(title="OpenReview.AI")
templates = Jinja2Templates(directory="templates")

class PRSubmission(BaseModel):
    author: str
    title: str
    diff: str

def submit_to_hedera_hcs(message: str) -> dict:
    print("DEBUG: [Hedera] Starting transaction build...")
    operator_id = os.getenv("HEDERA_OPERATOR_ID")
    operator_key = os.getenv("HEDERA_OPERATOR_KEY")
    topic_id = os.getenv("HEDERA_TOPIC_ID")

    # Graceful fallback if Hedera testnet keys are missing
    if not all([operator_id, operator_key, topic_id]):
        print("DEBUG: [Hedera] Keys missing, falling back to MOCK mode.")
        return {"receipt": f"MOCK-TX-{int(time.time())}", "url": None}

    try:
        from hiero_sdk_python.client.client import Client
        from hiero_sdk_python.crypto.private_key import PrivateKey
        from hiero_sdk_python.consensus.topic_message_submit_transaction import TopicMessageSubmitTransaction
        from hiero_sdk_python import TopicId, AccountId

        client = Client.for_testnet()
        client.set_operator(AccountId.from_string(operator_id), PrivateKey.from_string(operator_key))

        transaction = (
            TopicMessageSubmitTransaction()
            .set_topic_id(TopicId.from_string(topic_id))
            .set_message(message)
        )

        print("DEBUG: [Hedera] Executing transaction on testnet...")
        tx_response = transaction.execute(client)

        tx_id_str = str(tx_response.transaction_id).replace('@', '-').replace('.', '-')
        url = f"https://hashscan.io/testnet/transaction/{tx_id_str}"
        print(f"DEBUG: [Hedera] Success! URL: {url}")

        return {"receipt": str(tx_response.transaction_id), "url": url}
    except Exception as e:
        print(f"DEBUG: [Hedera] FAILED with error: {str(e)}")
        return {"receipt": f"Error: {str(e)}", "url": None}

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.post("/api/review")
async def process_pull_request(pr: PRSubmission):
    print(f"\n--- NEW PR RECEIVED: {pr.title} ---")
    
    # 1. Generate AI Code Review
    print("DEBUG: [AI] Sending code to Gemini...")
    try:
        prompt = (
            "You are an expert AI code reviewer. Analyze the code diff and provide a concise, "
            "actionable review summarizing bugs, security issues, or improvements.\n\n"
            f"Title: {pr.title}\n\nDiff:\n{pr.diff}"
        )
        # Using the new SDK syntax
        response = gemini_client.models.generate_content(
            model='gemini-3.5-flash',
            contents=prompt
        )
        ai_review = response.text
        print("DEBUG: [AI] Review generated successfully!")
    except Exception as e:
        print(f"DEBUG: [AI] FAILED with error: {str(e)}")
        ai_review = f"AI Error: {str(e)}"

    # 2. Log Verification to Hedera HCS
    hcs_payload = json.dumps({
        "event": "PR_REVIEWED",
        "author": pr.author,
        "title": pr.title,
        "status": "Verified by OpenReview.AI"
    })
    hedera_result = submit_to_hedera_hcs(hcs_payload)

    print("--- PR PROCESSING COMPLETE ---\n")
    return {
        "ai_review": ai_review,
        "hedera_receipt": hedera_result["receipt"],
        "tx_url": hedera_result["url"]
    }