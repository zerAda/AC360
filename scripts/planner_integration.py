import httpx
from safe_logger import log_security

GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"


async def create_planner_task(token: str, plan_id: str, bucket_id: str, title: str, due_date: str) -> dict:
    """
    Crée une tâche dans Microsoft Planner au nom de l'utilisateur de manière asynchrone.
    Nécessite la permission déléguée `Tasks.ReadWrite`.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "planId": plan_id,
        "bucketId": bucket_id,
        "title": title,
        "dueDateTime": due_date
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GRAPH_API_BASE}/planner/tasks",
            headers=headers,
            json=payload,
            timeout=10.0
        )

        if response.status_code == 201:
            return response.json()
        else:
            log_security("ERROR", f"Erreur API Graph: {response.text}")
            response.raise_for_status()


async def get_user_plans(token: str) -> list:
    """
    Récupère la liste des plans Planner de l'utilisateur de manière asynchrone.
    """
    headers = {
        "Authorization": f"Bearer {token}"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GRAPH_API_BASE}/me/planner/plans",
            headers=headers,
            timeout=10.0
        )

        if response.status_code == 200:
            return response.json().get("value", [])
        else:
            response.raise_for_status()
