from dotenv import load_dotenv
load_dotenv()
from json_data_preprocessor import DataPreprocessor
import logging
import os


if __name__ == "__main__":
    input_dir = os.environ.get("JSON_DIR")
    tokenizer_model = os.environ.get("TOKENIZER_MODEL")
    data_process = DataPreprocessor(input_dir=input_dir, model=tokenizer_model)
    # data_process = DataPreprocessor(input_dir=input_dir, model= embedding_model)
    data_process.run_preprocess_and_store_to_db(json_path=input_dir)
    logging.info("Finished processing all JSONs")
