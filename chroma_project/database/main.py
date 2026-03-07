import asyncio
import logging
import requests
import os
from dotenv import load_dotenv
load_dotenv()
from chromadb.utils import embedding_functions
import json

from chromadb_manager import ChromaDBManager
from data_processing.json_data_preprocessor import DataPreprocessor


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def check_format_of_env():
    errors = []
    
    json_dir = os.getenv("JSON_DIR", "")
    chroma_db_dir = os.getenv("CHROMA_DB_DIR", "")
    db_name = os.getenv("DB_NAME", "")

    print("Checking environment variables...\n")

    # JSON_DIR check
    if not json_dir or not json_dir.endswith(".json") or not os.path.exists(json_dir):
        errors.append(f"❌ JSON_DIR invalid: {json_dir}")
    else:
        print(f"✅ JSON_DIR OK: {json_dir}")

    # CHROMA_DB_DIR check
    expected_chroma = f"./chromadb/{os.path.basename(json_dir).split('.')[0]}_chromadb"
    if chroma_db_dir != expected_chroma:
        errors.append(f"❌ CHROMA_DB_DIR mismatch: got {chroma_db_dir}, expected {expected_chroma}")
    else:
        print(f"✅ CHROMA_DB_DIR OK: {chroma_db_dir}")

    # DB_NAME check
    expected_db = f"{os.path.basename(json_dir).split('.')[0]}_sql.db" if json_dir else None
    if not db_name or not db_name.endswith(".db"):
        errors.append(f"❌ DB_NAME invalid: {db_name}")
    elif expected_db and db_name != expected_db:
        errors.append(f"❌ DB_NAME mismatch: got {db_name}, expected {expected_db}")
    else:
        print(f"✅ DB_NAME OK: {db_name}")

    if errors:
        print("\n⚠️ Found issues:")
        for e in errors:
            print(e)
        return False
    return True


def check_format_of_dataset(json_path):
    print(f"\nChecking dataset format for {json_path}...\n")
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Failed to read JSON file: {e}")
        return False

    required_keys = ["document", "question", "answer", "ori_doc_title"]
    errors = []

    for key in required_keys:
        if key not in data:
            errors.append(f"❌ Missing key: {key}")
        elif not isinstance(data[key], list):
            errors.append(f"❌ {key} should be a list, got {type(data[key])}")

    if errors:
        print("\n⚠️ Found issues:")
        for e in errors:
            print(e)
        return False

    print("✅ Dataset format OK")
    return True



def send_telegram_message(message: str):
    token = "8013643521:AAEncrdXp-Xii93zSaFpr4UlN1LIQXPo64I"
    chat_id = "1744072683"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    try:
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            print("Failed to send Telegram message:", response.text)
    except Exception as e:
        print("Error sending Telegram message:", e)

async def process_sql_db():
    input_dir = os.environ.get("JSON_DIR")
    tokenizer_model = os.environ.get("TOKENIZER_MODEL")

    if not input_dir or not tokenizer_model:
        logging.error("Missing required environment variables: JSON_DIR or TOKENIZER_MODEL")
        raise ValueError("Missing environment variables")

    logging.info("Starting JSON preprocessing and storing to SQL")
    data_processor = DataPreprocessor(input_dir=input_dir, model=tokenizer_model)
    data_processor.run_preprocess_and_store_to_db(json_path=input_dir)
    logging.info("Finished processing all JSON files and storing to SQL")
    send_telegram_message(f"✅ Process finished with sql in {input_dir}")

async def process_chromadb():
    logging.info("Starting ChromaDB processing pipeline")

    google_api_key = os.environ.get("GOOGLE_API_KEY")
    if not google_api_key:
        logging.error("GOOGLE_API_KEY is not set")
        raise ValueError("GOOGLE_API_KEY environment variable not set")

    db_name = os.environ.get("DB_NAME")
    if not db_name:
        logging.error("DB_NAME is not set")
        raise ValueError("DB_NAME environment variable not set")

    logging.info("Initializing embedding function with Google Generative AI")
    # google_ef = embedding_functions.GoogleGenerativeAiEmbeddingFunction(
    #     api_key=google_api_key)
    # google_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    # model_name= "sentence-transformers/all-mpnet-base-v2")
    
    google_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="nomic-ai/nomic-embed-text-v1",
        trust_remote_code=True)
    
    logging.info("Creating ChromaDBManager instance")
    chroma_manager = ChromaDBManager(embedding_functions=google_ef)

    logging.info("Fetching data from SQL DB")
    data_by_sheet = chroma_manager.data_ingestion_manager.get_data_from_sql(db_name)

    for size, records in data_by_sheet.items():
        logging.info(f"Adding {len(records)} records to collection: {size}")
        chroma_manager.add_to_collection(size, records)

    chroma_manager.close()
    logging.info("ChromaDBManager closed and all data ingested successfully")
    send_telegram_message(f"✅ Process finished with chroma in {db_name}")

   
async def main():
    await process_sql_db()
    await process_chromadb()

if __name__ == "__main__":
    load_dotenv()
    proceed = False  # flag to control execution

    if check_format_of_env():
        json_file = os.getenv("JSON_DIR")
        if json_file and check_format_of_dataset(json_file):
            user_input = input("\nAll checks passed. Type 'yes' to proceed sql and chromadb: ")
            if user_input.strip().lower() == "yes":
                print("👉 Proceeding to next process...")
                proceed = True
            else:
                print("⛔ Process aborted by user.")
        else:
            print("⛔ Dataset format check failed.")
    else:
        print("⛔ Environment format check failed.")

    if proceed:
        asyncio.run(main())
    else:
        # stop program cleanly
        exit(1)