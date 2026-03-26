## **🌟 System Overview**

*Adaptive Document Chunking Size Selection Method for Retrieval Enhanced Large Language Models*

Our study aims **to address a fundamental limitation of fixed-size chunking** in RAG systems, where retrieval similarity score often favors smaller chunks at the cost of contextual completeness. To overcome this limitation, we propose **an adaptive chunking strateg**y that enables the retrieval system to utilize multiple chunk sizes simultaneously, rather than relying on a single fixed granularity. 

The proposed method consists of two core modules: a Hierarchical Chunking Strategy (HCS) and a Chunk Selection Mechanism (CSM). 

- **The Hierarchical Chunking Strategy** is integrated into the initial stage of an automated data processing pipeline and **segments each document into three levels of granularity**: 512-token, 256-token, and 128-token chunks. This multi-level representation allows the retrieval model to access information at different contextual scopes, enabling more flexible and context-aware retrieval behavior. Larger chunks preserve global context, while smaller chunks provide fine-grained semantic matching. To support scalability and reproducibility, the automated data pipeline converts structured JSON inputs into vector embeddings and stores them in ChromaDB. This design simplifies low-level processing details, enabling users to concentrate mainly on preparing input instead of manually managing data.
- While HCS improves retrieval flexibility, it also provides overlapping and redundant content across chunk levels. To address this issue, we introduce a **Chunk Selection Mechanism** that **filters duplicated information across different granularities**. The mechanism prioritizes contextual coherence while reducing token redundancy, ensuring that only the most relevant and non-overlapping chunks are retained. Based on similarity scores and token budget constraints, the final set of retrieved chunks is selected to maximize both relevance and contextual coverage for downstream generation.

![Picture1.png](attachment:19957f77-bf4c-48ca-a86b-c864b0a96ac8:Picture1.png)

**🎯 Core Components** 

- **📄 Hierarchical Chunking Strategy -** We carefully process documents into a hierarchical structure, generating multiple chunk sizes and applying a padding strategy to maintain consistency by using an effective chunking in data processing within our RAG pipeline.
- **🔄 Automated Data Pipeline -** Initially, we implemented a manual data preparation step to collect raw data from official sources, data ingestion, and convert them into vector embeddings stored in ChromaDB. Based on this workflow, we further developed a fully automated pipeline that allows audiences to focus only on input preparation.
- **🧠 Chunk Selection Mechanism -** We design a rule-based filtering approach to identify and select the most important and various content. This one guarantees that the retrieved documents are relevant, non-overlapping, and compact, thereby improving the quality of input provided to the LLM during generation.
- 🧮 **Retrieval Scoring Strategy -** Presenting the method used to calculate similarity scores and justifying the choice of our method.

---

## **🏗️ Algorithm & Architecture**

### Core Algorithms

Our method implements **an effective pipeline** that fundamentally extends traditional RAG architectures to seamlessly accommodate diverse content, enhance accuracy, and reduce token cost.

---

### **1. Preparing Data for RAG System Evaluation and Validation**

This study utilizes four datasets: **Natural Questions**, **TriviaQA**, **QuAC**, and

**NarrativeQA** with details in Table below. These datasets were selected because they

contain long documents, diverse question types, and, most importantly, grounded

answers that serve as a critical reference for validating retrieved documents.

![Screenshot 2026-03-26 at 3.47.39 PM.png](attachment:123b2ab0-534b-4a54-a284-40f357075c56:Screenshot_2026-03-26_at_3.47.39_PM.png)

---

### 2. Automated Pipeline for Data Ingestion and Vector Indexing

An automated workflow designed to convert JSON-formatted data into vector embeddings that are stored in ChromaDB including data ingestion and storage in ChromaDB. Besides, in order to carry out the automated pipeline, a manual data preparation step is performed to then transform these selected samples into a unified JSON structure, and after verifying that the input files comply with the predefined schema, the data are processed in a series of automated steps.

![Picture2.png](attachment:84df534f-fba9-4ec5-a97d-aeb84ce8f730:Picture2.png)

**Key concepts:**

- **The Hierarchical Chunking Strategy**: is implemented to segment each document into three levels of granularity: 512-token, 256-token, and 128-token chunks allowing us to meet the experimental requirements and evaluate performance across multiple chunk sizes.

![Picture3.png](attachment:d8f988b5-8eff-4472-a1fd-a1f99c86b042:Picture3.png)

- **Data Ingestion into SQLite:** Loading the input JSON raw data files and verifying whether they conform to a predefined schema. If yes, we implements a hierarchical text preprocessing pipeline to support structured storage within a SQLite relational database.

- **Vector Storage in ChromaDBs**: We apply vector indexing to store vector embeddings to separate ChromaDB collections. Besides, the system requires configuration of HNSW parameters for the three collections corresponding to different chunk sizes.

---

### 3. **Chunk Selection Mechanism**

Storing documents in multiple chunk sizes introduces the challenge of redundant tokens. For instance, during the retrieval process, both 512-token and 128-token chunks may be fetched simultaneously. However, if a 512-token chunk has a high similarity score and already encompasses the information contained in the 128-token chunk, retrieving the smaller chunk becomes unnecessary. Besides, token inefficiency is a well-recognized issue in RAG systems, where redundant and irrelevant retrievals can significantly degrade both efficiency and performance. 

→ We implement a hierarchical CSM that assists us to identify and select the most crucial chunks and various content across different levels of granularity to ensure efficient retrieval and maintain contextual coherence.

![Picture4.png](attachment:69f14a53-1709-409d-be67-87270c39a1b2:Picture4.png)

**Key concepts:**

- **Adaptive Multi-Granularity Filtering**: Dynamically selects between smaller and larger chunks using similarity thresholds. Smaller chunks are preferred when they provide higher precision, while larger chunks are selected only when they offer clear contextual advantage.
- **Normalized Similarity Scoring Strategy**: Uses normalized embeddings to ensure consistent similarity computation, preventing magnitude distortion and improving retrieval reliability.
- **L2 Distance-Based Similarity Transformation**: Converts squared Euclidean distance into a bounded similarity score range [-1, 1], maintaining interpretability while leveraging the efficiency of L2 distance in vector databases.
    
    ![Screenshot 2026-03-26 at 3.44.06 PM.png](attachment:cea7c941-b513-4524-9e2c-49cccc3132ca:Screenshot_2026-03-26_at_3.44.06_PM.png)
    

Given that the range of cos(𝜃) spans from [−1,1], and the squared Euclidean distance between normalized vectors lies within [0,4], we can transform the distance metric to align with the familiar similarity range. To achieve this, we define a new similarity function, denoted as “sim,” by rearranging the expression accordingly:

![Screenshot 2026-03-26 at 3.44.32 PM.png](attachment:040c9847-2c80-4e38-8631-8826d85240cb:Screenshot_2026-03-26_at_3.44.32_PM.png)

---

### 4. Evaluation Metrics

In our experiments, similarity scores between queries and retrieved documents
are initially analyzed to understand the behavior of the retrieval model and its scoring
characteristics. However, similarity scores alone do not directly reflect retrieval
effectiveness with respect to user relevance. Therefore, a second stage of evaluation
is conducted using these metrics: Mean Average Precision (MAP), Mean Reciprocal
Rank (MRR), and normalized Discounted Cumulative Gain (nDCG), to rigorously
assess ranking quality and retrieval performance. For comparison, a baseline retrieval
system is constructed, referred to as the Naive RAG system. This baseline uses a fixed chunk size, and for clarity in our evaluation, we denote its variants as Baseline-
512, Baseline-256, and Baseline-128, corresponding to the chunk size adopted in
each setting. This naming method allows us to directly compare the effectiveness of
our proposed adaptive chunking approach against traditional fixed-size retrieval
strategies.

**Key Concepts:**

- **Similarity-Based Retrieval Quality Assessment:** computing the mean similarity score between the query embeddings and the retrieved document embeddings.

![Screenshot 2026-03-26 at 3.39.07 PM.png](attachment:78e2ac8b-f089-4a95-9d63-6eb47340f6f7:Screenshot_2026-03-26_at_3.39.07_PM.png)

- **Mean Average Precision (MAP):**  is used to evaluate retrieval performance by computing the average precision for each query and then taking the mean over all queries. In our experiment, we apply a relevance threshold of **similarity ≥ 0.65**, consistent with the setting adopted in the MRR evaluation.

![Screenshot 2026-03-26 at 3.40.28 PM.png](attachment:5c558c14-6fd1-416c-b9db-a9038babf8d1:Screenshot_2026-03-26_at_3.40.28_PM.png)

- **Mean Reciprocal Rank (MRR):** measures how quickly the first relevant document appears within the ranked retrieval results. Specifically, it is computed as the average of the reciprocal rank of the first relevant document across all queries. The same relevance threshold (≥ 0.65) is used to determine whether a document is considered relevant
    
    ![Screenshot 2026-03-26 at 3.43.25 PM.png](attachment:38cdb7d6-1b8d-4091-baf3-7bbebe4c06cd:Screenshot_2026-03-26_at_3.43.25_PM.png)
    

---

### 5. Overall System Architecture

The system is designed for efficient retrieval by separating offline data processing from online query execution. It leverages hierarchical chunking and multi-scale vector storage to improve retrieval quality, while a containerized backend ensures scalable and reliable deployment.

![Picture5.png](attachment:881bf4e5-6397-49f4-990d-aa89e8ab5803:Picture5.png)

- **Multi-Database Vector Retrieval System**: Maintains four independent ChromaDB databases (Natural Questions, TriviaQA, QuAC, NarrativeQA), each containing multiple collections with different chunk sizes (128, 256, 512 tokens) to support adaptive and efficient similarity-based retrieval.
- **Containerized Backend Service Architecture**: Deploys all services using Docker on an Ubuntu 24.04 LTS server. A Flask-based RESTful API processes user queries, interacts with vector databases, and applies the Chunk Selection Mechanism to return relevant results.
- **Private Docker Registry Management**: Utilizes a dedicated private Docker registry hosted on a separate Ubuntu virtual machine to securely store and manage container images, ensuring controlled and reliable deployments without reliance on public repositories.
- **Interactive GUI for Retrieval Comparison**: Provides a user-friendly interface that displays retrieved chunks in a structured table format, enabling side-by-side comparison between the proposed method and baseline chunking strategies with visible similarity scores.
- **On-Demand Detailed Content Inspection**: Allows users to click on retrieved results to open a pop-up view showing full, untruncated content across methods, supporting deeper qualitative analysis of retrieval relevance and completeness.

---

## **💾** System Requirements

- **RAM:** Minimum 8 GB
- **Disk Space:** At least 50 GB
- **Python:** `>= 3.12`

---

## **🔧 Configuration**

### **Environment Variables**

Create a `.env` file (refer to `.env.example`):

```jsx
JSON_DIR="./dataset/natural_question.json"
CHROMA_DB_DIR="./chromadb/natural_question_chromadb"
DB_NAME="natural_question_sql.db"

HUGGINGFACE_API_KEY=""
GOOGLE_API_KEY=""
TELEGRAM_KEY=""

TOKENIZER_MODEL="meta-llama/Llama-3.2-1B"
```

> ⚠️ **Important:** 
You must provide valid API keys for:
- Hugging Face
- Google Gemini
- Telegram
> 

---

## **🚀 Quick Launch for local host**

### Windows

```
python-m venv env
env\Scripts\activate

pip install--upgrade pip
pip install-r requirements.txt

python app.py
```

### Linux

```
sudo apt install python3-venv

python3-m venv env
source env/bin/activate

pip install--upgrade pip
pip install-r requirements.txt

python app.py
```

⚠️ Notes

- This project uses **ChromaDB**, which depends on `chroma-hnswlib`.
- On Windows, you must install:

> **Microsoft Visual C++ 14.0 or greater**
> 

Download from:

https://visualstudio.microsoft.com/visual-cpp-build-tools/

---

## **📖 Citation**

*Academic Reference*
<div align="center">
📖
</div>
If you find our adaptive chunk strategy useful in your research, please cite our paper:

```
@misc{key,
  author = {VU QUANG HUY and CHEN JIAN-RU},
  title = {Adaptive Document Chunking Size Selection Method for Retrieval Enhanced Large Language Models},
  year = {2026},
  url = {https://hdl.handle.net/11296/4622jk}
}
```
