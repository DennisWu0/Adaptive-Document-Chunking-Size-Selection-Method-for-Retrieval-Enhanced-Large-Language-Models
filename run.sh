# Build the Docker image
docker build -t adaptive-chunks-test .


# docker run --gpus all -p 5007:5007 \
#     -v $(pwd)/.env:/app/.env \
#     -v /home/dennis/workspace/adaptive_chunksize/chromadb/narrativeqa_chromadb/:/app/chromadb/narrativeqa_chromadb \
#     -v /home/dennis/workspace/adaptive_chunksize/chromadb/natural_question_chromadb/:/app/chromadb/natural_question_chromadb \
#     -v /home/dennis/workspace/adaptive_chunksize/chromadb/quac_chromadb/:/app/chromadb/quac_chromadb \
#     -v /home/dennis/workspace/adaptive_chunksize/chromadb/triviaqa_chromadb/:/app/chromadb/triviaqa_chromadb \
#     adaptive-chunks

# Run the container
docker run --gpus all -p 5007:5007 \
    -v $(pwd)/.env:/app/.env \
    -v ./chromadb/natural_question_chromadb/:/app/chromadb/natural_question_chromadb \
    adaptive-chunks-test

