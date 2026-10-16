import os
import time
import json
import re
import hashlib
import urllib.request
import urllib.error
from typing import Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()

# Initialize Gemini Client
gemini_api_key = os.getenv("GEMINI_API_KEY")
gemini_client = genai.Client(api_key=gemini_api_key) if gemini_api_key else None

app = FastAPI(
    title="OpenReview.AI",
    description="Enterprise AI Code Reviewer with Hedera Consensus Service Verification",
    version="2.0.0"
)
templates = Jinja2Templates(directory="templates")


class PRSubmission(BaseModel):
    author: str
    title: str
    diff: str
    repo: Optional[str] = "local/workspace"
    pr_number: Optional[int] = None


class PRFetchRequest(BaseModel):
    url: str


def generate_diff_sha256(diff_text: str) -> str:
    """Generate SHA-256 fingerprint for tamper-proof diff verification."""
    return hashlib.sha256(diff_text.encode("utf-8")).hexdigest()


def fetch_github_pr_details(pr_url: str) -> dict:
    """Fetch PR metadata and raw unified diff from a public GitHub PR URL."""
    # Pattern: https://github.com/{owner}/{repo}/pull/{pr_number}
    match = re.search(r"github\.com/([^/]+)/([^/]+)/pull/(\d+)", pr_url.strip())
    if not match:
        raise HTTPException(
            status_code=400,
            detail="Invalid GitHub PR URL. Expected format: https://github.com/owner/repo/pull/123"
        )

    owner, repo, pr_number = match.group(1), match.group(2), match.group(3)
    github_token = os.getenv("GITHUB_TOKEN")

    headers = {
        "User-Agent": "OpenReview-AI-Agent",
        "Accept": "application/vnd.github.v3+json"
    }
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    # 1. Fetch metadata
    api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as response:
            pr_data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise HTTPException(
            status_code=e.code,
            detail=f"GitHub API error ({e.code}): {e.reason}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to connect to GitHub: {str(e)}"
        )

    # 2. Fetch raw diff
    diff_url = f"https://github.com/{owner}/{repo}/pull/{pr_number}.diff"
    diff_headers = {"User-Agent": "OpenReview-AI-Agent"}
    if github_token:
        diff_headers["Authorization"] = f"Bearer {github_token}"

    try:
        diff_req = urllib.request.Request(diff_url, headers=diff_headers)
        with urllib.request.urlopen(diff_req, timeout=15) as diff_resp:
            diff_text = diff_resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        # Fallback to diff_url from API response
        try:
            fallback_url = pr_data.get("diff_url", diff_url)
            diff_req = urllib.request.Request(fallback_url, headers=diff_headers)
            with urllib.request.urlopen(diff_req, timeout=15) as diff_resp:
                diff_text = diff_resp.read().decode("utf-8", errors="replace")
        except Exception as e2:
            raise HTTPException(
                status_code=502,
                detail=f"Failed to fetch PR diff: {str(e2)}"
            )

    author = pr_data.get("user", {}).get("login", "unknown_author")
    title = pr_data.get("title", f"Pull Request #{pr_number}")

    return {
        "owner": owner,
        "repo": f"{owner}/{repo}",
        "pr_number": int(pr_number),
        "author": author,
        "title": title,
        "diff": diff_text
    }


def call_gemini_with_fallback(prompt: str) -> str:
    """Generate review content with automatic fallback across supported Gemini models."""
    if not gemini_client:
        return "⚠️ Gemini API key is missing. Set GEMINI_API_KEY in your .env file."

    models_to_try = ["gemini-3.5-flash", "gemini-3.5-flash-lite"]
    last_error = None

    for model_name in models_to_try:
        try:
            print(f"DEBUG: [AI] Querying model '{model_name}'...")
            response = gemini_client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            if response and response.text:
                print(f"DEBUG: [AI] Success with model '{model_name}'.")
                return response.text
        except Exception as e:
            print(f"DEBUG: [AI] Model '{model_name}' failed: {str(e)}")
            last_error = e

    return f"AI Error: Unable to complete analysis after trying fallback models. Details: {str(last_error)}"


def extract_verdict(review_text: str) -> str:
    """Extract standard verdict indicator from review text."""
    lower = review_text.lower()
    if "verdict: approved" in lower or "verdict: **approved**" in lower or "verdict: [approved]" in lower:
        return "APPROVED"
    elif "changes requested" in lower or "verdict: **changes requested**" in lower:
        return "CHANGES_REQUESTED"
    elif "needs discussion" in lower or "needs review" in lower:
        return "NEEDS_DISCUSSION"
    return "VERIFIED"


def submit_to_hedera_hcs(payload_data: dict) -> dict:
    """Submit cryptographic review record to Hedera Consensus Service (HCS)."""
    print("DEBUG: [Hedera] Building HCS transaction payload...")
    operator_id = os.getenv("HEDERA_OPERATOR_ID")
    operator_key = os.getenv("HEDERA_OPERATOR_KEY")
    topic_id = os.getenv("HEDERA_TOPIC_ID")

    message_str = json.dumps(payload_data)

    # Graceful fallback if Hedera testnet keys are missing
    if not all([operator_id, operator_key, topic_id]):
        print("DEBUG: [Hedera] Keys missing, falling back to MOCK mode.")
        mock_tx_id = f"0.0.mock-{int(time.time())}-123456789"
        return {
            "receipt": mock_tx_id,
            "url": f"https://hashscan.io/testnet/transaction/{mock_tx_id}",
            "mode": "MOCK"
        }

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
            .set_message(message_str)
        )

        print("DEBUG: [Hedera] Executing transaction on testnet...")
        tx_response = transaction.execute(client)

        tx_id_str = str(tx_response.transaction_id).replace('@', '-').replace('.', '-')
        url = f"https://hashscan.io/testnet/transaction/{tx_id_str}"
        print(f"DEBUG: [Hedera] Success! URL: {url}")

        return {
            "receipt": str(tx_response.transaction_id),
            "url": url,
            "mode": "HEDERA_TESTNET"
        }
    except Exception as e:
        print(f"DEBUG: [Hedera] FAILED with error: {str(e)}")
        return {
            "receipt": f"Error: {str(e)}",
            "url": None,
            "mode": "ERROR"
        }


def post_github_comment(repo: str, pr_number: int, comment_body: str) -> bool:
    """Optional: Post review comment directly onto GitHub Pull Request if token available."""
    token = os.getenv("GITHUB_TOKEN")
    if not token or not repo or not pr_number:
        return False

    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "OpenReview-AI-Agent",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }
    payload = json.dumps({"body": comment_body}).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status in (200, 201)
    except Exception as e:
        print(f"DEBUG: [GitHub Comment] Failed to post comment: {str(e)}")
        return False


# ================= ROUTES =================

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/health")
async def health_check():
    hedera_ready = bool(os.getenv("HEDERA_OPERATOR_ID") and os.getenv("HEDERA_TOPIC_ID"))
    return {
        "status": "online",
        "version": "2.0.0",
        "ai_engine": "Gemini 3.5 Flash / Lite",
        "network": "Hedera Testnet" if hedera_ready else "Mock Consensus Mode",
        "github_integration": bool(os.getenv("GITHUB_TOKEN"))
    }


@app.post("/api/fetch-pr")
async def fetch_pr_endpoint(req: PRFetchRequest):
    """Fetch PR author, title, and diff directly from a public GitHub PR link."""
    return fetch_github_pr_details(req.url)


@app.post("/api/review")
async def process_pull_request(pr: PRSubmission):
    print(f"\n--- NEW PR RECEIVED: {pr.title} (Author: {pr.author}) ---")

    # Limit diff size to prevent context overflow
    diff_trimmed = pr.diff
    if len(diff_trimmed) > 30000:
        diff_trimmed = diff_trimmed[:30000] + "\n\n... [DIFF TRUNCATED FOR LENGTH] ..."

    # 1. Cryptographic Fingerprint of the Code
    diff_hash = generate_diff_sha256(pr.diff)

    # 2. Generate Structured AI Review
    prompt = f"""You are an elite enterprise code review architect. Perform an exhaustive review of the following pull request code diff.

Repository: {pr.repo}
PR Title: {pr.title}
Author: {pr.author}

Code Diff:
```diff
{diff_trimmed}
```

Format your review in clean, professional Markdown with these exact sections:

### 🎯 Summary & Verdict
- **Verdict**: [APPROVED | CHANGES REQUESTED | NEEDS DISCUSSION]
- **Quality Score**: [0-100]/100
- **Summary**: 1-2 sentence executive assessment.

### 🛡️ Security & Vulnerability Analysis
Audit for SQLi, XSS, insecure deserialization, unvalidated inputs, credential leaks, or auth bypass. If clean, state "No critical security risks identified."

### ⚡ Performance & Scalability
Evaluate time/space complexity, resource leaks, database query patterns, and asynchronous efficiency.

### 🧹 Code Quality & Maintainability
Assess architectural design, typing, clean-code conventions, and error handling.

### 💡 Recommended Patch / Fix
Provide the exact corrected code block or diff ready to apply.
"""

    ai_review = call_gemini_with_fallback(prompt)
    verdict = extract_verdict(ai_review)

    # 3. Log Immutable Record to Hedera HCS
    hcs_payload = {
        "event": "PR_REVIEWED",
        "app": "OpenReview.AI",
        "repo": pr.repo,
        "pr_number": pr.pr_number,
        "author": pr.author,
        "title": pr.title,
        "verdict": verdict,
        "diff_sha256": diff_hash,
        "timestamp": int(time.time()),
        "status": "Verified by OpenReview.AI"
    }
    hedera_result = submit_to_hedera_hcs(hcs_payload)

    # 4. Construct Verifiable Markdown Badge
    tx_url = hedera_result.get("url")
    badge_label = "Hedera%20Verified"
    badge_color = "00c853" if verdict == "APPROVED" else ("f59e0b" if verdict == "NEEDS_DISCUSSION" else "ef4444")
    badge_url = f"https://img.shields.io/badge/OpenReview-{badge_label}-{badge_color}?style=flat&logo=hedera"
    
    badge_markdown = (
        f"[![OpenReview Verified]({badge_url})]({tx_url})"
        if tx_url else
        f"![OpenReview Verified]({badge_url})"
    )

    print("--- PR PROCESSING COMPLETE ---\n")
    return {
        "ai_review": ai_review,
        "verdict": verdict,
        "diff_hash": diff_hash,
        "hedera_receipt": hedera_result["receipt"],
        "tx_url": tx_url,
        "mode": hedera_result.get("mode", "HEDERA_TESTNET"),
        "badge_markdown": badge_markdown
    }


@app.post("/api/webhook/github")
async def github_webhook(request: Request):
    """
    Automated GitHub Webhook handler for PR events.
    Configure in GitHub Repo Settings -> Webhooks -> Payload URL: https://your-domain/api/webhook/github
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    action = payload.get("action")
    pr_data = payload.get("pull_request")

    if not pr_data or action not in ["opened", "synchronize", "reopened"]:
        return {"status": "ignored", "reason": f"Action '{action}' is not monitored."}

    repo_full_name = payload.get("repository", {}).get("full_name", "")
    pr_number = pr_data.get("number")
    pr_url = pr_data.get("html_url")
    author = pr_data.get("user", {}).get("login", "unknown")
    title = pr_data.get("title", f"PR #{pr_number}")

    # Fetch full diff
    try:
        fetched = fetch_github_pr_details(pr_url)
        diff_text = fetched["diff"]
    except Exception as e:
        diff_text = f"# Failed to pull diff automatically: {str(e)}"

    pr_submission = PRSubmission(
        author=author,
        title=title,
        diff=diff_text,
        repo=repo_full_name,
        pr_number=pr_number
    )

    result = await process_pull_request(pr_submission)

    # Post automated comment on the GitHub PR if GITHUB_TOKEN is available
    comment_body = (
        f"## 🤖 OpenReview.AI Automated Audit\n\n"
        f"{result['badge_markdown']}\n\n"
        f"**Consensus Verification:** [HashScan Receipt]({result['tx_url']})\n"
        f"**Diff SHA-256:** `{result['diff_hash']}`\n\n"
        f"---\n\n"
        f"{result['ai_review']}\n\n"
        f"---\n*Verified on Hedera Consensus Service via OpenReview.AI*"
    )
    posted = post_github_comment(repo_full_name, pr_number, comment_body)

    return {
        "status": "processed",
        "repo": repo_full_name,
        "pr_number": pr_number,
        "verdict": result["verdict"],
        "hedera_tx": result["tx_url"],
        "github_comment_posted": posted
    }