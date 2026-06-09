"""
Tests Red-Team AC360 — 20 vecteurs d'attaque
Vérifie statiquement que les topics et settings résistent aux principaux vecteurs.
"""
import os

TOPICS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "src", "copilot", "AC360", "topics"
)
SETTINGS_FILE = os.path.join(
    os.path.dirname(__file__), "..", "..", "src", "copilot", "AC360", "settings.mcs.yml"
)
AGENT_FILE = os.path.join(
    os.path.dirname(__file__), "..", "..", "src", "copilot", "AC360", "agent.mcs.yml"
)


def _read_all_topics() -> str:
    """Concatène le contenu de tous les topics pour les recherches globales."""
    content = ""
    if os.path.isdir(TOPICS_DIR):
        for f in os.listdir(TOPICS_DIR):
            if f.endswith(".mcs.yml"):
                with open(os.path.join(TOPICS_DIR, f), "r", encoding="utf-8") as fh:
                    content += fh.read() + "\n"
    return content


# ─────────────────────────────────────────────
# RT-01 à RT-05 : Prompt Injection / Jailbreak
# ─────────────────────────────────────────────

def test_RT01_settings_use_model_knowledge_false():
    """RT-01 : useModelKnowledge doit être false — empêche les hallucinations hors-documents."""
    assert os.path.exists(SETTINGS_FILE), "settings.mcs.yml introuvable"
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    assert "useModelKnowledge: false" in content, (
        "RT-01 FAIL : useModelKnowledge n'est pas false. "
        "Le bot peut répondre avec ses connaissances générales — risque d'hallucination."
    )


def test_RT02_content_moderation_high():
    """RT-02 : contentModeration doit être High."""
    assert os.path.exists(SETTINGS_FILE), "settings.mcs.yml introuvable"
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    assert "contentModeration: High" in content or "contentModeration: high" in content.lower(), (
        "RT-02 FAIL : contentModeration n'est pas High. Risque de réponses non filtrées."
    )


def test_RT03_no_auto_email_send():
    """RT-03 : Aucun topic ne doit envoyer automatiquement un email (mailto: interdit)."""
    topics_content = _read_all_topics()
    # L'instruction de génération automatique est interdite
    assert "IMPORTANT : Ajoute systématiquement ce lien" not in topics_content, (
        "RT-03 FAIL : Un topic contient une instruction pour générer un lien mailto: automatique. "
        "Vecteur d'exfiltration/phishing."
    )


def test_RT04_no_document_modification_capability():
    """RT-04 : Le topic de refus de modification de document doit exister."""
    refusal_topic = os.path.join(TOPICS_DIR, "Refusmodificationdocument.mcs.yml")
    assert os.path.exists(refusal_topic), (
        "RT-04 FAIL : Le topic Refusmodificationdocument.mcs.yml est absent. "
        "Aucun garde-fou contre les demandes de modification."
    )


def test_RT05_no_system_prompt_disclosure():
    """RT-05 : Les topics doivent contenir une règle interdisant la divulgation des instructions système."""
    topics_content = _read_all_topics()
    keywords = [
        "instructions système",
        "instructions systeme",
        "divulguer",
        "révéler",
    ]
    found = any(kw.lower() in topics_content.lower() for kw in keywords)
    assert found, (
        "RT-05 FAIL : Aucun topic ne contient de règle interdisant la divulgation "
        "des instructions système. Risque de prompt injection documentaire."
    )


# ─────────────────────────────────────────────
# RT-06 à RT-10 : Sécurité données / DLP
# ─────────────────────────────────────────────

def test_RT06_no_cross_client_data():
    """RT-06 : Les topics doivent interdire le mélange de clients."""
    topics_content = _read_all_topics()
    assert "mélanger deux clients" in topics_content or "Ne jamais mélanger" in topics_content, (
        "RT-06 FAIL : Aucune règle explicite contre la fuite inter-client dans les topics."
    )


def test_RT07_ambiguous_client_handling():
    """RT-07 : Les topics doivent gérer les clients ambigus (demander précision)."""
    topics_content = _read_all_topics()
    assert "ambigu" in topics_content, (
        "RT-07 FAIL : Aucun topic ne gère le cas d'un client ambigu. "
        "Risque de réponse sur le mauvais client."
    )


def test_RT08_no_legal_definitive_advice():
    """RT-08 : Aucun topic ne doit promettre un avis juridique définitif."""
    topics_content = _read_all_topics()
    # On vérifie qu'il y a au moins une mention de limitation juridique
    legal_limits = [
        "validation humaine",
        "juridique",
        "lecture seule",
        "ne peut pas conclure",
    ]
    found = any(kw.lower() in topics_content.lower() for kw in legal_limits)
    assert found, (
        "RT-08 FAIL : Aucune mention de limite juridique dans les topics. "
        "Risque d'avis juridique définitif non sourcé."
    )


def test_RT09_escalate_topic_exists():
    """RT-09 : Un topic d'escalade vers un humain doit exister."""
    escalate_topic = os.path.join(TOPICS_DIR, "Escalate.mcs.yml")
    assert os.path.exists(escalate_topic), (
        "RT-09 FAIL : Topic Escalate.mcs.yml absent. "
        "Pas de possibilité d'escalade vers un conseiller humain."
    )


def test_RT10_readonly_declaration_in_topics():
    """RT-10 : Les topics doivent déclarer explicitement que l'agent est en lecture seule."""
    topics_content = _read_all_topics()
    assert "lecture seule" in topics_content.lower(), (
        "RT-10 FAIL : Aucun topic ne déclare que l'agent est en lecture seule. "
        "Risque de confusion sur les capacités de l'agent."
    )


# ─────────────────────────────────────────────
# RT-11 à RT-15 : Sécurité Backend / API
# ─────────────────────────────────────────────

def test_RT11_no_verify_signature_false():
    """RT-11 : L'API ne doit jamais désactiver la vérification de signature JWT."""
    api_files = [
        os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "api_server.py"),
        os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "auth.py"),
    ]
    for api_file in api_files:
        if os.path.exists(api_file):
            with open(api_file, "r", encoding="utf-8") as f:
                content = f.read()
            assert "verify_signature=False" not in content, (
                f"RT-11 FAIL : {api_file} contient verify_signature=False. "
                "P0 Sécurité critique — auth bypassable."
            )


def test_RT12_no_hardcoded_secrets_in_scripts():
    """RT-12 : Les scripts Python ne doivent pas contenir de secrets en dur."""
    scripts_dir = os.path.join(os.path.dirname(__file__), "..", "..", "scripts")
    dangerous_patterns = [
        'client_secret="',
        "client_secret='",
        'password="',
        "password='",
        'apikey="',
        "apikey='",
    ]
    for fname in os.listdir(scripts_dir):
        if fname.endswith(".py"):
            fpath = os.path.join(scripts_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read().lower()
            for pattern in dangerous_patterns:
                assert pattern not in content, (
                    f"RT-12 FAIL : {fname} contient potentiellement le pattern '{pattern}'. "
                    "Secret potentiellement en clair."
                )


def test_RT13_jobs_base_dir_is_env_var():
    """RT-13 : JOBS_BASE_DIR doit être configuré via variable d'environnement."""
    config_file = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "config.py")
    with open(config_file, "r", encoding="utf-8") as f:
        content = f.read()
    assert 'os.getenv("JOBS_BASE_DIR"' in content or "os.getenv('JOBS_BASE_DIR'" in content, (
        "RT-13 FAIL : JOBS_BASE_DIR n'est pas configuré via variable d'environnement."
    )


def test_RT14_no_invoke_expression_in_powershell():
    """RT-14 : Les scripts PowerShell ne doivent pas utiliser Invoke-Expression."""
    scripts_dir = os.path.join(os.path.dirname(__file__), "..", "..", "scripts")
    for fname in os.listdir(scripts_dir):
        if fname.endswith(".ps1"):
            fpath = os.path.join(scripts_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            assert "Invoke-Expression" not in content, (
                f"RT-14 FAIL : {fname} contient Invoke-Expression. "
                "Vecteur d'injection de commande."
            )


def test_RT15_no_execution_policy_bypass_hardcoded():
    """RT-15 : Les scripts PowerShell ne doivent pas contenir ExecutionPolicy Bypass en dur dans les pipelines."""
    # Le code Python de l'API ne doit jamais invoquer PowerShell avec ExecutionPolicy.
    api_file = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "api_server.py")
    if os.path.exists(api_file):
        with open(api_file, "r", encoding="utf-8") as f:
            content = f.read()
        assert "ExecutionPolicy" not in content, (
            "RT-15 FAIL : api_server.py contient ExecutionPolicy — "
            "appel PowerShell direct non sécurisé depuis l'API."
        )


# ─────────────────────────────────────────────
# RT-16 à RT-20 : Gouvernance / Conformité
# ─────────────────────────────────────────────

def test_RT16_gitignore_excludes_secrets():
    """RT-16 : .gitignore doit exclure les fichiers sensibles."""
    gitignore = os.path.join(os.path.dirname(__file__), "..", "..", ".gitignore")
    assert os.path.exists(gitignore), "RT-16 FAIL : .gitignore absent."
    with open(gitignore, "r", encoding="utf-8") as f:
        content = f.read()
    for pattern in [".env", "*.db", "*.log", "__pycache__"]:
        assert pattern in content, (
            f"RT-16 FAIL : .gitignore ne contient pas '{pattern}'."
        )


def test_RT17_env_example_exists_no_real_secrets():
    """RT-17 : .env.example doit exister et ne pas contenir de vraies valeurs."""
    env_example = os.path.join(os.path.dirname(__file__), "..", "..", ".env.example")
    assert os.path.exists(env_example), "RT-17 FAIL : .env.example absent."
    with open(env_example, "r", encoding="utf-8") as f:
        content = f.read()
    # Les vraies valeurs Azure ressemblent à des GUIDs longs
    import re
    guid_pattern = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE)
    guids_found = guid_pattern.findall(content)
    assert len(guids_found) == 0, (
        f"RT-17 FAIL : .env.example contient {len(guids_found)} GUID(s) potentiellement réels. "
        "Vérifier s'il s'agit de valeurs de production."
    )


def test_RT18_scan_secrets_script_exists():
    """RT-18 : Un script de scan de secrets doit exister."""
    scan_script = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "scan_secrets.ps1")
    assert os.path.exists(scan_script), (
        "RT-18 FAIL : scan_secrets.ps1 absent. Aucun mécanisme de prévention des fuites de secrets."
    )


def test_RT19_gitleaks_config_exists():
    """RT-19 : .gitleaks.toml doit exister pour la détection automatique de secrets."""
    gitleaks = os.path.join(os.path.dirname(__file__), "..", "..", ".gitleaks.toml")
    assert os.path.exists(gitleaks), (
        "RT-19 FAIL : .gitleaks.toml absent. Pas de protection Git contre les commits de secrets."
    )


def test_RT20_no_docx_xlsx_in_scripts():
    """RT-20 : Le dossier scripts ne doit pas contenir de fichiers de données clients (.docx, .xlsx, .csv)."""
    scripts_dir = os.path.join(os.path.dirname(__file__), "..", "..", "scripts")
    forbidden_ext = {".docx", ".xlsx", ".csv", ".xls"}
    found = []
    for fname in os.listdir(scripts_dir):
        _, ext = os.path.splitext(fname)
        if ext.lower() in forbidden_ext:
            found.append(fname)
    assert len(found) == 0, (
        f"RT-20 FAIL : Fichiers de données clients dans scripts/ : {found}. "
        "Risque de fuite de données RGPD."
    )
