import logging
import re
import unicodedata
import uuid
from transformers import AutoTokenizer
from pathlib import Path
from .sqlite_db import SQLiteDB  # Import the SQLiteDB class
import json
import os


# Configure logging
logging.basicConfig(
    filename="process.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

class DataPreprocessor:
    def __init__(self, input_dir, model):
        self.input_dir = Path(input_dir)
        # Get the Hugging Face token from the environment variable
        hf_token = os.environ.get("HUGGINGFACE_API_KEY")
        # Pass the token to from_pretrained
        self.tokenizer = AutoTokenizer.from_pretrained(model, token=hf_token)
        logging.info("Initialized DataPreprocessor with input directory: %s and model: %s", input_dir, model)

    def read_title(self, json_path) -> list:
        """Extracts the title from a json file."""
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)

            title = data.get('ori_doc_title')
            logging.info("Extracted title from %s: %s", json_path, title)
            return title
        except Exception as e:
            logging.error("Error extracting title from %s: %s", json_path, e)
            return "No Title Found"
    
        # try:
        #     doc = fitz.open(pdf_path)
        #     metadata = doc.metadata
        #     title = metadata.get("title", "No Title Found")
        #     logging.info("Extracted title from %s: %s", pdf_path, title)
        #     return title
        # except Exception as e:
        #     logging.error("Error extracting title from %s: %s", pdf_path, e)
        #     return "No Title Found"

    def read_document(self, json_path) -> list:
        """Load all paragraphs from a json file."""
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)

            document = data.get('document')
            logging.info("✅ Extracted document from %s", json_path)
            return document
        except Exception as e:
            logging.error("Error extracting title from %s: %s", json_path, e)
            return "No Document Found"


        # logging.info("Loading all paragraphs, excluding files: %s", exclude_files)
        # reader = SimpleDirectoryReader(input_dir=str(self.input_dir), exclude=exclude_files)
        # docs = reader.load_data()
        # logging.info("Loaded %d documents", len(docs))
        # return "".join(doc.text for doc in docs)
    
    def generate_uuid(self):
        """Generates a UUID."""
        uuid_str = str(uuid.uuid4())
        logging.info("Generated UUID: %s", uuid_str)
        return uuid_str
    
    def clean_text(self, text):
        """Normalize special characters and remove extra spaces."""
        cleaned_text = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip()
        logging.info("Cleaned text length: %d", len(cleaned_text))
        return cleaned_text
    
    def split_into_tokens(self, text):
        """Convert text into tokenized form."""
        tokens = self.tokenizer.tokenize(text)
        logging.info("Tokenized text into %d tokens", len(tokens))
        return tokens

    def detokenize(self, tokens):
        """Convert tokens back into readable text."""
        return self.tokenizer.convert_tokens_to_string(tokens)
    
    def split_fixed_size(self, tokens, size):
        """Strictly split tokens into equal-sized chunks."""
        chunks = [tokens[i:i + size] for i in range(0, len(tokens), size)]
        logging.info("Split tokens into %d chunks of size %d", len(chunks), size)
        return chunks
    
    def pad_tokens(self, tokens, block_size=512):
        token_length = len(tokens)

        # Calculate how much padding is needed
        if token_length % block_size != 0:
            lack_tokens = token_length % block_size
            padding_needed = block_size - lack_tokens
        else:
            padding_needed = 0
        # Only pad if padding is needed
        if padding_needed > 0:
            logging.info("Added %d tokens for padding", padding_needed)
            if token_length >= padding_needed:
                pad_chunk = tokens[-padding_needed:]  # last N tokens
            else:
                # If there aren't enough tokens, repeat the whole list
                pad_chunk = (tokens * ((padding_needed // len(tokens)) + 1))[:padding_needed]
            
            tokens.extend(pad_chunk)
      
        return tokens


    #the main method in this class
    def process_chunks(self, tokens, ori_doc_title, db, chunk_level1=512, chunk_level2=256, chunk_level3=128):
        """Process and store chunks with metadata in the SQLite database."""
        padded_tokens = self.pad_tokens(tokens)
        chunks = self.split_fixed_size(padded_tokens, chunk_level1)
        
        for paragraph, chunk in enumerate(chunks, start=1):
            chunk_id = self.generate_uuid()
            document = self.detokenize(chunk)
            db.insert_chunk("chunks_512", chunk_id, document, ori_doc_title, paragraph, chunk_level1, 1)

            for sub_index, chunk_256 in enumerate(self.split_fixed_size(chunk, chunk_level2)):
                chunk_id_256 = self.generate_uuid()
                document_256 = self.detokenize(chunk_256)
                chunk_level_256 = 2 if sub_index % 2 == 0 else 3
                db.insert_chunk("chunks_256", chunk_id_256, document_256, ori_doc_title, paragraph, chunk_level2, chunk_level_256)

                for sub_sub_index, chunk_128 in enumerate(self.split_fixed_size(chunk_256, chunk_level3)):
                    chunk_id_128 = self.generate_uuid()
                    document_128 = self.detokenize(chunk_128)
                    new_chunk_level = 4 + sub_index * 2 + sub_sub_index
                    db.insert_chunk("chunks_128", chunk_id_128, document_128, ori_doc_title, paragraph, chunk_level3, new_chunk_level)
        logging.info("Finished processing chunks for document: %s", ori_doc_title)

    # def process_article(self, pdf_path):
    #     """Main function to process a PDF document and store hierarchical chunks in the database."""
    #     logging.info("Processing PDF: %s", pdf_path)
    #     ori_doc_title = self.read_title(pdf_path)
    #     text = self.clean_text(self.read_document([Path(pdf_path).name]))
    #     tokens = self.split_into_tokens(text)
    #     return tokens, ori_doc_title
    

    def run_preprocess_and_store_to_db(self, json_path):
        """Main function to process a document and store hierarchical chunks in the database."""
        # logging.info("Processing JSON: %s", json_path)
        # ori_doc_title = self.read_title(json_path)
        # text = self.clean_text(self.read_document(json_path))
        # tokens = self.split_into_tokens(text)
        # return tokens, ori_doc_title
        db = SQLiteDB()
        try:
            db.connect()
            db.create_tables()

            ori_doc_titles = self.read_title(json_path)
            for i in range(len(ori_doc_titles)):
                ori_doc_title = ori_doc_titles[i]
                text = self.clean_text(self.read_document(json_path)[i])
                tokens = self.split_into_tokens(text)
                
                self.process_chunks(tokens, ori_doc_title, db)


        except Exception as e:
            logging.error("Error processing JSON: %s", e)

        finally:
            db.close()

    
    # def run_preprocess_and_store_to_db(self):
    #     """Process all PDFs in the directory and store the chunks in an SQLite database."""
    #     logging.info("Starting to process all PDFs in directory: %s", self.input_dir)
    #     db = SQLiteDB()
    #     try:
    #         db.connect()
    #         db.create_tables()
    #         for pdf_path in self.input_dir.glob("*.pdf"):
    #             logging.info("Processing: %s", pdf_path)
    #             tokens, ori_doc_title = self.process_article(pdf_path)
    #             self.process_chunks(tokens, ori_doc_title, db)
    #             logging.info("Finished processing: %s", pdf_path)
    #             logging.info("\n --- \n")
    #     except Exception as e:
    #         logging.error("Error processing PDFs: %s", e)
    #     finally:
    #         db.close()
