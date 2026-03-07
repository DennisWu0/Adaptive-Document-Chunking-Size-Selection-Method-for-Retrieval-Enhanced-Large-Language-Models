import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'chroma_project/database')))

import json
from flask import Flask, request, render_template, jsonify
from dotenv import load_dotenv
from chroma_project.main import process_query

load_dotenv()

CONFIG_FILE = "config.json"

def load_config():
    config = {
        "JSON_DIR": os.getenv("JSON_DIR", ""),
        "CHROMA_DB_DIR": os.getenv("CHROMA_DB_DIR", ""),
        "DB_NAME": os.getenv("DB_NAME", "")
    }
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            file_config = json.load(f)
            config.update(file_config)
    return config

def save_config(new_config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(new_config, f, indent=4)

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    current_config = load_config()
    if request.method == "POST":
        query = request.form["query"]
        # Assuming process_query is defined in main.py
        answers, relevant_chunks_dicts, target_lists, base_lines = process_query(query)

        data = {
            "question": query,
            "ground_truth": 'The World Social Forum ( WSF , Portuguese : Fórum Social Mundial ( ˈfɔɾũ sosiaw mũdʒiaw ) ) is an annual meeting of civil society organizations , first held in Brazil , which offers a self - conscious effort to develop an alternative future through the championing of counter-hegemonic globalization . The World Social Forum can be considered a visible manifestation of global civil society , bringing together non governmental organizations , advocacy campaigns , and formal and informal social movements seeking international solidarity . The World Social Forum prefers to define itself as `` an opened space -- plural , diverse , non-governmental and non-partisan -- that stimulates the decentralized debate , reflection , proposals building , experiences exchange and alliances among movements and organizations engaged in concrete actions towards a more solidarity , democratic and fair world ... a permanent space and process to build alternatives to neoliberalism . '' It is held by members of the alter - globalization movement ( also referred to as the global justice movement ) who come together to coordinate global campaigns , share and refine organizing strategies , and inform each other about movements from around the world and their particular issues . The World Social Forum is explicit about not being a representative of all of those who attend and thus does not publish any formal statements on behalf of participants . It tends to meet in January at the same time as its great capitalist rival, the World Economic Forums Annual Meeting in Davos , Switzerland . This date is consciously picked to promote alternative answers to world economic problems in opposition to the World Economic Forum.',
            "method_answer": answers,
            "relevant_chunks_method": relevant_chunks_dicts,
            "relevant_chunks_baseline1": target_lists[0],
            "relevant_chunks_baseline2": target_lists[1],
            "relevant_chunks_baseline3": target_lists[2],
            "baselines": base_lines,
            "config": current_config
        }
        
        return render_template("index.html", data=data)
        
    return render_template("index.html", data={"question": None, "config": current_config})

@app.route("/save_config", methods=["POST"])
def save_configuration():
    new_config = request.get_json()
    if new_config:
        save_config(new_config)
        return jsonify({"status": "success", "message": "Configuration saved successfully."})
    return jsonify({"status": "error", "message": "Invalid configuration data."}), 400

# if __name__ == "__main__":
#     app.run(debug=True)
if __name__ == '__main__':
    # This is how you would run the app in production
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5007)), debug=True)

# python -m gunicorn -w 4 -b 0.0.0.0:5007 app:app
