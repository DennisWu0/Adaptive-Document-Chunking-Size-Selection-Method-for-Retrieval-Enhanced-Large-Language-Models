# Step1: reformat and then place to this directory 
# /home/dennis/workspace/adaptive_chunksize/dataset
# and make the data's format like below 
#{
#  "document": [],
#  "question": [],
#  "answer": [],
#  "ori_doc_title": []
#}

# Step2: adjust .env file

# Step3: run
python chroma_project/database/main.py 
