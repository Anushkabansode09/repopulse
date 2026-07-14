import os
import requests
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("GITHUB_TOKEN")

headers = {"Authorization": f"Bearer {token}"}
response = requests.get("https://api.github.com/repos/psf/requests", headers=headers)

print(response.status_code)
print(response.json().get("full_name"))