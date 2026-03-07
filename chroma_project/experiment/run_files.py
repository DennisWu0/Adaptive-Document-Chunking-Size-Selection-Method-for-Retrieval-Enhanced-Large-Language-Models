import subprocess
import requests


def run_script(script_path):
    try:
        subprocess.run(['python', script_path], check=True)
        print(f"Successfully ran {script_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error running {script_path}: {e}")

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

# 5000 39 19 9
# 4500 35 17 8
# 4000 31 15 7
# 3500 27 13 6
# 3000 23 11 5

if __name__ == "__main__":
# 0.005 0.0075 0.01 0.0125 0.015 0.0175
    script1_path = "/home/dennis/workspace/adaptive_chunksize/chroma_project/experiment/ex_on_article.py"
    script2_path = "/home/dennis/workspace/adaptive_chunksize/chroma_project/experiment/ex_on_my_method.py"

    process1 = subprocess.Popen(['python', script1_path])
    process2 = subprocess.Popen(['python', script2_path])

    process1.wait()
    process2.wait()

    send_telegram_message("Done")
