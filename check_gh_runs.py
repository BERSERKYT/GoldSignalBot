import requests

def check_runs():
    url = "https://api.github.com/repos/BERSERKYT/GoldSignalBot/actions/runs"
    response = requests.get(url)
    if response.status_code == 200:
        runs = response.json().get('workflow_runs', [])
        print(f"Total runs found: {len(runs)}")
        for i, run in enumerate(runs[:5]):
            print(f"[{i}] Status: {run['status']} | Conclusion: {run['conclusion']} | Name: {run['name']} | Event: {run['event']} | Created: {run['created_at']}")
    else:
        print(f"Failed to fetch: {response.status_code} - {response.text}")

if __name__ == "__main__":
    check_runs()
