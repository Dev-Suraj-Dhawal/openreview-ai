import os
from dotenv import load_dotenv
from hiero_sdk_python import Client, AccountId, PrivateKey, TopicCreateTransaction

load_dotenv()

def create_hedera_topic():
    operator_id = os.getenv("HEDERA_OPERATOR_ID")
    operator_key = os.getenv("HEDERA_OPERATOR_KEY")

    if not operator_id or not operator_key:
        print("Error: Missing Hedera credentials in .env file.")
        return

    # Initialize the testnet client
    client = Client.for_testnet()
    client.set_operator(AccountId.from_string(operator_id), PrivateKey.from_string(operator_key))

    print("Creating topic on Hedera testnet...")
    
    # Build and execute the topic creation transaction
    transaction = TopicCreateTransaction()
    transaction.topic_memo = "OpenReview.AI Logs"
    
    # execute() directly returns the TransactionReceipt in the Hiero Python SDK
    receipt = transaction.execute(client)
    topic_id = receipt.topic_id
    
    print(f"✅ Success! Your new Topic ID is: {topic_id}")

if __name__ == "__main__":
    create_hedera_topic()