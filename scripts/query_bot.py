import subprocess
import json


def run():
    # Get token
    cmd = 'az account get-access-token --resource https://org2cf282f3.crm4.dynamics.com'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print("Error getting token:", result.stderr)
        return
    token = json.loads(result.stdout)['accessToken']

    import urllib.parse
    base_url = "https://org2cf282f3.api.crm4.dynamics.com/api/data/v9.2/bots"
    query = "?$filter=botid eq 'c82f127c-8f47-f111-bec6-000d3ab9a512'"
    url = base_url + urllib.parse.quote(query, safe="?=$'")
    req = urllib.request.Request(url, headers={
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json',
        'OData-MaxVersion': '4.0',
        'OData-Version': '4.0'
    })

    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            print(json.dumps(data, indent=2))
    except urllib.error.URLError as e:
        print("HTTP Error:", e.reason)
        if hasattr(e, 'read'):
            print(e.read().decode())


if __name__ == "__main__":
    run()
