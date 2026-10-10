# OpenReview.AI 🚀

**OpenReview.AI** is an open-source AI assistant that automates code reviews for pull requests and securely logs contributor credentials on the Hedera decentralized network.

Built for the **Hacktoberfest Hack Day Bhairahawa X Graphilla Technology Private Limited** hackathon.

## 🏆 Hackathon Tracks

* **Best Use of Hedera:** Utilizes the Hedera Consensus Service (HCS) to log immutable records of merged pull requests, providing verifiable proof of open-source contributions.

* **DigitalOcean - Best Open Source AI Project:** Fully open-source AI backend designed to be deployed on DigitalOcean Droplet infrastructure.

## ✨ Features

* **AI Code Review:** Automatically analyzes code diffs using OpenAI's LLMs to provide actionable feedback on bugs, security, and improvements.

* **Decentralized Verification:** Logs a permanent, immutable record of the review to the Hedera testnet.

* **Built-in Fallback:** Includes a mock-mode for testing if Hedera credentials are not yet configured.

* **Clean UI:** Simple, fast dashboard built with Tailwind CSS and FastAPI.

## 🛠️ Built With

* Python & FastAPI

* OpenAI API (gpt-4o-mini)

* Hedera Python SDK (`hiero-sdk-python`)

* Jinja2 & Tailwind CSS

## 🚀 Getting Started

### Prerequisites

* Python 3.10+

* [OpenAI API Key](https://platform.openai.com/api-keys)

* [Hedera Developer Portal Account](https://portal.hedera.com/) (Testnet)

### Installation

1. **Clone the repository**

   ```
   git clone https://github.com/YOUR_USERNAME/openreview-ai.git
   cd openreview-ai
   
   ```

2. **Create a virtual environment**

   ```
   python -m venv .venv
   
   # Windows:
   .\.venv\Scripts\activate
   
   # macOS/Linux:
   source .venv/bin/activate
   
   ```

3. **Install dependencies**

   ```
   pip install -r requirements.txt
   
   ```

4. **Environment Setup**
   Create a `.env` file in the root directory and add your keys:

   ```
   OPENAI_API_KEY=your_openai_key
   HEDERA_OPERATOR_ID=0.0.xxxxx
   HEDERA_OPERATOR_KEY=30300...
   HEDERA_TOPIC_ID=
   
   ```

5. **Generate a Hedera Topic ID**
   Run the setup script to register your topic on the testnet:

   ```
   python create_topic.py
   
   ```

   *Copy the output ID and paste it into your `.env` file.*

6. **Run the Application**

   ```
   uvicorn main:app --reload
   
   ```

   Open `http://127.0.0.1:8000` in your browser.