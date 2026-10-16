# OpenReview.AI 🚀

**OpenReview.AI** is an enterprise-grade open-source AI assistant that automates pull request code reviews, generates actionable security and performance audits, and securely logs tamper-proof cryptographic proofs on the **Hedera Consensus Service (HCS)**.

Built for **Hacktoberfest Hack Day Bhairahawa X Graphilla Technology Private Limited**.

---

## 🏆 Hackathon Tracks

* **Best Use of Hedera:** Utilizes the Hedera Consensus Service (HCS) to log immutable records of pull request reviews with SHA-256 diff fingerprints, providing verifiable proof of code quality and open-source contributions.
* **DigitalOcean - Best Open Source AI Project:** Fully open-source AI backend deployable on DigitalOcean Droplets and App Platform.

---

## ✨ Features

* **Instant GitHub PR Ingestion:** Paste any public GitHub Pull Request URL (`https://github.com/owner/repo/pull/123`) to automatically fetch PR metadata, author, and code diff.
* **Autonomous GitHub Webhook Bot:** Connect `POST /api/webhook/github` to repository webhooks to automatically audit PRs on creation and post review comments with verification badges.
* **Structured Enterprise AI Audits:** Powered by Google Gemini (with automatic model resilience) delivering:
  * 🎯 **Summary & Verdict** (`APPROVED`, `CHANGES REQUESTED`, `NEEDS DISCUSSION`) with Quality Scores.
  * 🛡️ **Security & Vulnerability Analysis** (SQLi, XSS, auth bypass, secret leaks).
  * ⚡ **Performance & Scalability** (complexity, memory leaks, query optimizations).
  * 🧹 **Code Quality & Best Practices** (typing, clean code conventions).
  * 💡 **Actionable Patch / Fix** (ready-to-apply diff snippets).
* **Decentralized Verification on Hedera HCS:** Submits an immutable consensus record with timestamp, author, repository, verdict, and SHA-256 diff hash.
* **Verifiable GitHub Badges:** Generates copyable Markdown badges pointing to HashScan explorer receipts for contributors to embed in PRs and READMEs.
* **Interactive Presets:** One-click sample audits (SQL Injection, Async Resource Leak, Clean Feature).
* **Mac-Terminal Bento UI:** Sleek spatial dashboard with live line numbers, Marked.js Markdown rendering, and Highlight.js syntax highlighting.

---

## 🛠️ Tech Stack

* **Backend:** Python 3.10+, FastAPI, Uvicorn, Pydantic
* **AI Intelligence:** Google GenAI SDK (`gemini-3.5-flash` / `gemini-3.5-flash-lite`)
* **Decentralized Ledger:** Hedera Python SDK (`hiero-sdk-python`) on Hedera Consensus Service (HCS)
* **Frontend:** Tailwind CSS, Jinja2, Lucide Icons, Marked.js, Highlight.js
* **Deployment:** Vercel (`vercel.json`) & DigitalOcean Droplet

---

## 🚀 Getting Started

### Prerequisites

* Python 3.10+
* [Google AI Studio API Key](https://aistudio.google.com/)
* [Hedera Developer Portal Account](https://portal.hedera.com/) (Testnet)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Dev-Suraj-Dhawal/openreview-ai.git
   cd openreview-ai
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv .venv

   # Windows:
   .\.venv\Scripts\activate

   # macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   Create a `.env` file in the root directory:
   ```env
   GEMINI_API_KEY=your_gemini_api_key
   HEDERA_OPERATOR_ID=0.0.xxxxx
   HEDERA_OPERATOR_KEY=30300...
   HEDERA_TOPIC_ID=0.0.xxxxx

   # Optional: For automated GitHub PR comments
   GITHUB_TOKEN=ghp_your_personal_access_token
   ```

5. **Generate a Hedera Topic ID (If not already created)**
   ```bash
   python create_topic.py
   ```
   *Copy the output Topic ID into your `.env`.*

6. **Run the Application**
   ```bash
   uvicorn main:app --reload
   ```
   Open `http://127.0.0.1:8000` in your browser.

---

## 🤖 GitHub Webhook Integration (Bot Mode)

To enable automatic reviews directly on your GitHub repository:

1. Go to your GitHub repository **Settings → Webhooks → Add webhook**.
2. **Payload URL:** `https://your-domain.com/api/webhook/github`
3. **Content type:** `application/json`
4. **Events:** Select **"Let me select individual events"** → Check **"Pull requests"**.
5. Set `GITHUB_TOKEN` in your server `.env` to allow the bot to post review comments and badges directly to the PR.

---

## 📄 License

MIT License. Open source and built for the community.