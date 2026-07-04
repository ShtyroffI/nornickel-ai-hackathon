import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("YANDEX_API_KEY")
folder_id = os.getenv("YANDEX_FOLDER_ID")

print(f"Using API Key: {api_key[:5]}...{api_key[-5:]}")
print(f"Using Folder ID: {folder_id}")

url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
headers = {
    "Authorization": f"Api-Key {api_key}",
    "x-folder-id": folder_id
}

data = {
    "modelUri": f"gpt://{folder_id}/yandexgpt-lite",
    "completionOptions": {
        "stream": False,
        "temperature": 0.3,
        "maxTokens": "100"
    },
    "messages": [
        {
            "role": "system",
            "text": "Ты тестовый ассистент."
        },
        {
            "role": "user",
            "text": "Скажи Привет мир"
        }
    ]
}

response = requests.post(url, headers=headers, json=data)

print(f"Status Code: {response.status_code}")
try:
    print(response.json())
except Exception as e:
    print(f"Error parsing JSON: {e}")
    print(response.text)
