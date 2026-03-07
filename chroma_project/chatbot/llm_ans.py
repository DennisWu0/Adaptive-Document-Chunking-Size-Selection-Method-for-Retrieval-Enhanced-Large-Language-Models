from dotenv import load_dotenv
load_dotenv()

import os
from llama_index.core.llms import ChatMessage
from llama_index.llms.google_genai import GoogleGenAI

# Set your API key securely
os.environ["GOOGLE_API_KEY"]

class GoogleGenAILLM:
    def __init__(self, model):
        self.model = model
        self.llm = GoogleGenAI(model=model)  # uses GOOGLE_API_KEY from env

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        """Handles multi-turn conversation with a system and user prompt."""
        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_prompt)
        ]
        response = self.llm.chat(messages)
        return response

    def stream_complete(self, prompt: str):
        raise NotImplementedError("Streaming not supported in this implementation.")

    @property
    def metadata(self):
        return {"model_name": self.model}


# Function to send relevant chunks to LLM
def query_llm(relevant_chunks: list[str], user_question: str) -> str:
    context = "\n\n".join(f"- {chunk}" for chunk in relevant_chunks)
    user_prompt = (
    f"Question: {user_question}\n\n"
    f"Please answer the above question based on the following information:\n\n{context}\n\nAnswer:"
)
    # user_prompt = f"{user_question}\n\nContext:\n{context}"
    system_prompt = "You are an AI assistant. Answer based on the provided context."

    # llm = GoogleGenAILLM(model="gemini-2.0-flash")
    llm = GoogleGenAILLM(model="gemini-2.5-flash")
    
    response = llm.chat(system_prompt, user_prompt)
    content = response.message.content.strip()
    if content.lower().startswith("assistant:"):
        content = content[len("assistant:"):].strip()
    
    return content

# def query_llm(relevant_chunks: list[str], user_question: str) -> str:
#     # Create context with labels for chunk size to guide LLM prioritization
#     context = "\n\n".join(
#         f"[Chunk size: {len(chunk.split())} tokens]\n{chunk}" for chunk in relevant_chunks
#     )

    # user_prompt = (
    #     f"You are given multiple text chunks of different sizes (512, 256, 128 tokens). "
    #     f"Larger chunks usually provide broader coverage, while smaller ones may give more detail. "
    #     f"Some chunks may overlap. Your task is to carefully combine them when answering.\n\n"
    #     f"User Question:\n{user_question}\n\n"
    #     f"Relevant Chunks (ordered by retrieval relevance):\n{context}\n\n"
    #     f"Instructions:\n"
    #     f"1. Base your answer only on the chunks provided. Do not use outside knowledge.\n"
    #     f"2. Prefer larger chunks for main context, but use smaller chunks to refine or add detail.\n"
    #     f"3. If chunks overlap, do not repeat information unnecessarily.\n"
    #     f"4. If no chunk contains enough information, say 'The context does not provide a clear answer.'\n\n"
    #     f"Answer:"
    # )

#     system_prompt = "You are a careful AI assistant. Answer strictly based on the provided context."

#     llm = GoogleGenAILLM(model="gemini-2.0-flash")
#     response = llm.chat(system_prompt, user_prompt)
#     content = response.message.content.strip()
#     if content.lower().startswith("assistant:"):
#         content = content[len("assistant:"):].strip()
    
#     return content
