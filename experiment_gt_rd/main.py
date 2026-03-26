from mongdb import MongoDBClient
from dotenv import load_dotenv
from chromadb.utils import embedding_functions
from chromadb.utils.distance_functions import l2
load_dotenv()
import os
import pandas as pd
from openpyxl import Workbook
import requests
import time
import logging

# Configure logging once at the top of your script
logging.basicConfig(
    filename="negative_scores.log",   # log file name
    level=logging.WARNING,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
# Configure logging

MONGO_URI = "mongodb://localhost:27017/"
# MONGO_DB_NAMES = ["narrativeqa_mongo", "natural_question_mongo", "quac_mongo", "triviaqa_mongo"]
MONGO_DB_NAMES = ["natural_question_mongo", "quac_mongo", "triviaqa_mongo"]

# MONGO_DB_NAMES = ["narrativeqa_mongo", "triviaqa_mongo_test_v3"]
# MONGO_DB_NAMES = ["quac_mongo", "natural_question_mongo", "quac_mongo", "triviaqa_mongo_test"]

COLLECTION_NAMES = ["128", "256", "512", "our_method"]
google_api_key = os.environ.get("GOOGLE_API_KEY")

# embedding_fn = embedding_functions.GoogleGenerativeAiEmbeddingFunction(
#     api_key=google_api_key)

embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="nomic-ai/nomic-embed-text-v1",
        trust_remote_code=True)

def compute_l2_distance(text1, text2, embedding_fn, retries=5, wait_time=300):
    """Compute L2 distance with retry on API errors."""
    for attempt in range(retries):
        try:
            gt_embedding = embedding_fn([text1])[0]
            chunk_embedding = embedding_fn([text2])[0]
            return l2(gt_embedding, chunk_embedding)
        except Exception as e:
            print(f"Error in compute_l2_distance: {e}")
            if attempt < retries - 1:  # Only wait if retries remain
                print(f"Retrying in {wait_time // 60} minutes... (attempt {attempt+1}/{retries})")
                time.sleep(wait_time)
            else:
                # If all retries fail, return a large distance so similarity becomes very low
                return float("inf")


def similarity_score(distance: float) -> float:
    """Converts L2 distance to a similarity score."""
    return 1.0 - distance / 2

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

try:
    output_dir = "experiment_gt_rd/ex_0927/k-0.01"
    os.makedirs(output_dir, exist_ok=True) 

    for MONGO_DB_NAME in MONGO_DB_NAMES:
        excel_name = f"mongo_ss_{MONGO_DB_NAME}.xlsx"
        
        excel_path = os.path.join(output_dir, excel_name)  
        excel_writer = pd.ExcelWriter(excel_path, engine="openpyxl")
        mongo = MongoDBClient(uri=MONGO_URI, db_name=MONGO_DB_NAME)

        for collection_name in COLLECTION_NAMES:
            documents = mongo.find(collection_name=collection_name, filter={})
            documents = documents[:300]  # take only first 100 and then do with 300 questions

            rows = []
            count=0
            for doc in documents:
                count +=1
                question = doc.get("question", "N/A")
                grounded_true = doc.get("grounded_answer", "")
                retrieved_chunks = doc.get("retrieved_chunks", [])
                print(f"Question{count}: Processing question: {question[:80]}...")
                scores = []
                for chunk in retrieved_chunks:
                    chunk_text = chunk.get("document", "")
                    distance = compute_l2_distance(grounded_true, chunk_text, embedding_fn)
                    score = similarity_score(distance)
                    if score < 0:
                        logging.warning(
                            f"Negative score detected. Question: {question[:80]} | "
                            f"Chunk: {chunk_text[:50]} | Score: {score}"
                        )

                    scores.append(score)

                # Prepend question to the list of scores
                row = [question] + scores
                rows.append(row)
      
            if rows:
                max_chunks = max(len(row) - 1 for row in rows)
                columns = ["Question"] + [f"Chunk {i+1}" for i in range(max_chunks)]

                for row in rows:
                    while len(row) < max_chunks + 1:
                        row.append(None)

                df = pd.DataFrame(rows, columns=columns)
            else:
                logging.warning(f"No documents found in {MONGO_DB_NAME}.{collection_name}")
                df = pd.DataFrame(columns=["Question"])

            df.to_excel(excel_writer, sheet_name=collection_name[:31], index=False)

        mongo.close()
        excel_writer.close()  # ✅ proper close instead of _save()
        print("\nMongoDB connection closed.")

    send_telegram_message(f"Done {excel_name}")

except Exception as e:
    print("Error in processing:", e)
    send_telegram_message(f"Error: {e}")


# if __name__ == '__main__':

# # ground_true = "Thompson said he planned to sue Take-Two/Rockstar in an effort to have both Manhunt 2 and Grand Theft Auto IV banned as \'public nuisances\'"
# # chunks= " of the defamatory reports): 'It has never been the Telegraph's case to suggest that the allegations contained in these documents are true'. The newspaper argued that it acted responsibly as the allegations it reported were of sufficient public interest to outweigh the damage caused to Galloway's reputation. The trial judge did not accept this defence, noting that comments such as Galloway being guilty of 'treason', 'in Saddam's pay', and being 'Saddam's little helper' caused him [the judge] to conclude that 'the newspaper was not neutral but both embraced the allegations with relish and fervour and went on to embellish them'; additionally, the judge ruled, Galloway had not been given a fair or reasonable opportunity to make inquiries or meaningful comment upon the documents before they were published. The issue of whether or not the documents were genuine was likewise not at issue at the trial. Oliver Thorne, a forensic expert who had been earlier hired by Galloway's lawyers, later stated 'In my opinion the evidence found fully supports that the vast majority of the submitted documents are authentic'. He added 'It should be noted that I am unable to comment on the veracity of the information within the disputed Telegraph documents, whether or not they are authentic."
# # chunks512= "John Bruce 'Jack' Thompson (born July 25, 1951) is an American activist and disbarred attorney, based in Coral Gables, Florida. Thompson is known for his role as an anti-video-game activist, particularly against violence and sex in video games. During his time as an attorney, Thompson focused his legal efforts against what he perceives as obscenity in modern culture. This included rap music, broadcasts by shock jock Howard Stern, the content of computer and video games and their alleged effects on children. During the aftermath of the murder of Stefan Pakeerah, by his friend Warren Leblanc in Leicestershire, England, the game Manhunt was linked after the media wrongfully claimed police found a copy in Leblanc's room. The police officially denied any link, citing drug-related robbery as the motive and revealing that the game had been found in Pakeerah's bedroom, not Leblanc's. Thompson, who had heard of the murder, claimed that he had written to Rockstar after the game was released, warning them that the nature of the game could inspire copycat killings: 'I wrote warning them that somebody was going to copycat the Manhunt game and kill somebody. We have had dozens of killings in the U.S. by children who had played these types of games. This is not an isolated incident. These types of games are basically murder simulators. There are people being killed over here almost on a daily basis.' Soon thereafter, the Pakeerah family hired Thompson with the aim of suing Sony and Rockstar for PS50 million in a wrongful death claim. Jack Thompson would later vow to permanently ban the game during the release of the sequel Manhunt 2. Thompson said he planned to sue Take-Two/Rockstar in an effort to have both Manhunt 2 and Grand Theft Auto IV banned as 'public nuisances', saying 'killings have been specifically linked to Take-Two's Manhunt and Grand Theft Auto games. [I have] asked Take-Two and retailers to stop selling Take-Two's 'Mature' murder simulation games to kids. They all refuse. They are about to be told by a court of law that they must adhere to the logic of their own 'Mature' labels. The suits were eradicated when Take-Two petitioned U.S. District Court, SD FL to block the impending lawsuit, on the grounds that video games purchased for private entertainment could not be considered public nuisances. The following day, Thompson wrote"
# # chunks256= "John Bruce 'Jack' Thompson (born July 25, 1951) is an American activist and disbarred attorney, based in Coral Gables, Florida. Thompson is known for his role as an anti-video-game activist, particularly against violence and sex in video games. During his time as an attorney, Thompson focused his legal efforts against what he perceives as obscenity in modern culture. This included rap music, broadcasts by shock jock Howard Stern, the content of computer and video games and their alleged effects on children. During the aftermath of the murder of Stefan Pakeerah, by his friend Warren Leblanc in Leicestershire, England, the game Manhunt was linked after the media wrongfully claimed police found a copy in Leblanc's room. The police officially denied any link, citing drug-related robbery as the motive and revealing that the game had been found in Pakeerah's bedroom, not Leblanc's. Thompson, who had heard of the murder, claimed that he had written to Rockstar after the game was released, warning them that the nature of the game could inspire copycat killings: 'I wrote warning them that somebody was going to copycat the Manhunt game and kill somebody. We have had dozens of killings in"
# # chunks128 = "John Bruce 'Jack' Thompson (born July 25, 1951) is an American activist and disbarred attorney, based in Coral Gables, Florida. Thompson is known for his role as an anti-video-game activist, particularly against violence and sex in video games. During his time as an attorney, Thompson focused his legal efforts against what he perceives as obscenity in modern culture. This included rap music, broadcasts by shock jock Howard Stern, the content of computer and video games and their alleged effects on children. During the aftermath of the murder of Stefan Pakeerah, by his friend Warren Leblanc in Le"

#     ground_true = "Parental involvement laws in the UK ; if the girl is seen as competent by medical staff no disclosure to parents is allowed . In most cases , girls aged 13 or above will be covered by this provision but pre-teenagers will not and parents , social workers and police can become involved to protect the child . Around 120 12 - year - olds , at least five 11 - year - olds and two nine - year - olds have had legal abortions since 1996 . In 2005 , Sue Axon , of Manchester , wanted the law changed to prevent girls under 16 getting confidential advice . However , the High Court had rejected a review of guidelines which state that terminations do not need parents ' consent and doctors should respect girls ' confidentiality ."
#     chunks ="I'm sorry, but I cannot answer the question as the context provided does not contain any information about abortion laws or age requirements in the UK. The text appears to be excerpts from Wikipedia pages and their associated discussions, covering topics such as file usage, licenses, and various Wikipedia-related administrative matters, but it does not include any legal or medical information related to abortion."


#     distance = compute_l2_distance( ground_true, chunks, embedding_fn)
#     # distance512 = compute_l2_distance( ground_true, chunks512, embedding_fn)
#     # distance256 = compute_l2_distance( ground_true, chunks256, embedding_fn)
#     # distance128 = compute_l2_distance( ground_true, chunks128, embedding_fn)

#     score = similarity_score(distance)
#     # score512 = similarity_score(distance512)

#     # score256 = similarity_score(distance256)

#     # score128 = similarity_score(distance128)

#     print("L2 Distance:", distance)
#     print("Similarity Score:", score)
#     # print("Similarity Score:", score512)
#     # print("Similarity Score:", score256)
#     # print("Similarity Score:", score128)
