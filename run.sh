# Build the Docker image
docker build -t adaptive-chunks .

# Run the container
docker run --gpus all -p 5007:5007 \
    -v $(pwd)/.env:/app/.env \
    -v ./chromadb/natural_question_chromadb/:/app/chromadb/natural_question_chromadb \
    -v ./natural_question_sql.db/:/app/natural_question_sql.db \
    adaptive-chunks

