from fastapi import FastAPI, Header, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import subprocess
import os
import time

app = FastAPI(
    title="AC360 Audit Engine API",
    description="API Enterprise Grade pour déclencher le pipeline Python depuis Copilot Studio",
    version="1.0.0"
)

# Schéma de requête
class AuditRequest(BaseModel):
    document_path: str
    client_context: Optional[str] = None

def run_audit_pipeline(doc_path: str, user_principal_name: str):
    """
    Exécute le pipeline d'audit en arrière-plan.
    En production, on utiliserait Celery ou Azure Functions.
    Ici, on appelle le script maître PowerShell local pour simuler l'orchestration complète.
    """
    try:
        # Tracer l'audit dans la DB
        from db_manager import log_audit_action
        log_audit_action(doc_path, "START_AUDIT", "IN_PROGRESS", f"Triggered by {user_principal_name}")
        
        # Appel simulé au pipeline (en réalité on appellerait .\scripts\run_audit_pipeline.ps1)
        # Mais pour la démonstration API, on attend quelques secondes et on logue le succès.
        time.sleep(3)
        
        log_audit_action(doc_path, "END_AUDIT", "SUCCESS", "Pipeline terminé avec succès.")
        print(f"[API_WORKER] Audit terminé pour {doc_path} par {user_principal_name}")
    except Exception as e:
        print(f"[API_WORKER_ERROR] {e}")

@app.post("/api/audit")
async def trigger_audit(request: AuditRequest, background_tasks: BackgroundTasks, x_user_upn: Optional[str] = Header(None)):
    """
    Déclenche un audit AC360 sur un document spécifique.
    Ceci est l'endpoint qui sera appelé par Copilot Studio.
    """
    if not x_user_upn:
        # Sécurité RBAC simulée : On exige de savoir qui fait la demande
        raise HTTPException(status_code=401, detail="X-User-UPN header manquant. Authentification requise.")

    if not os.path.exists(request.document_path):
        # On simule un document virtuel pour les tests
        if not request.document_path.startswith("mock://"):
            raise HTTPException(status_code=404, detail=f"Document introuvable : {request.document_path}")

    # Lancement de la tâche lourde en background pour ne pas bloquer le bot Copilot
    background_tasks.add_task(run_audit_pipeline, request.document_path, x_user_upn)

    return {
        "status": "success",
        "message": "L'audit a été lancé avec succès. Vous serez notifié via Teams à la fin du traitement.",
        "job_id": f"job_{int(time.time())}",
        "document": request.document_path,
        "requested_by": x_user_upn
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    # Lancement du serveur en local sur le port 8000
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)
