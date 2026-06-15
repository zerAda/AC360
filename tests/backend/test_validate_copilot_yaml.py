"""
Tests Wave-0 (PUB-04 + PUB-02) pour les 3 nouvelles assertions hors-ligne du
validateur Copilot Studio (`scripts/validate_copilot_yaml.py`).

- `find_agent_guardrail_issues(data, filename)` (PUB-04) : sur settings.mcs.yml,
  exige `useModelKnowledge` explicitement False et `contentModeration` == High.
  Réf. : learn.microsoft.com/microsoft-copilot-studio/knowledge-copilot-studio
  (useModelKnowledge scope le modèle aux sources de connaissances configurées —
  pas de "connaissance générale" présentée comme un fait client).
- branche fail-closed hôte staging de `find_wiring_issues(data)` (PUB-02) : tout
  HttpRequestAction visant ac360-gateway-staging.azurewebsites.net échoue après
  la bascule prod.

conftest.py injecte déjà `scripts/` dans sys.path — aucun fixture nécessaire.
"""
import validate_copilot_yaml as v


def _settings(use_model_knowledge=False, moderation="High"):
    """Construit une structure settings.mcs.yml minimale (configuration.aISettings)."""
    ai = {
        "isFileAnalysisEnabled": False,
        "isSemanticSearchEnabled": True,
        "contentModeration": moderation,
    }
    if use_model_knowledge is not None:
        ai["useModelKnowledge"] = use_model_knowledge
    return {"configuration": {"aISettings": ai}}


def _http_topic(url):
    """Construit un topic minimal avec un beginDialog -> HttpRequestAction.url."""
    return {
        "beginDialog": {
            "actions": [
                {
                    "kind": "HttpRequestAction",
                    "id": "http_call",
                    "method": "Post",
                    "url": url,
                }
            ]
        }
    }


def test_useModelKnowledge_false_passes():
    data = _settings(use_model_knowledge=False, moderation="High")
    assert v.find_agent_guardrail_issues(data, "settings.mcs.yml") == []


def test_useModelKnowledge_true_fails():
    data = _settings(use_model_knowledge=True, moderation="High")
    issues = v.find_agent_guardrail_issues(data, "settings.mcs.yml")
    assert issues, "useModelKnowledge=True doit produire une issue"


def test_useModelKnowledge_missing_fails():
    # aISettings présent mais SANS la clé useModelKnowledge -> doit échouer
    # (la valeur doit être explicitement False, pas seulement absente).
    data = _settings(use_model_knowledge=None, moderation="High")
    issues = v.find_agent_guardrail_issues(data, "settings.mcs.yml")
    assert issues, "useModelKnowledge absent doit produire une issue"


def test_moderation_not_high_fails():
    data = _settings(use_model_knowledge=False, moderation="Medium")
    issues = v.find_agent_guardrail_issues(data, "settings.mcs.yml")
    assert issues, "contentModeration != High doit produire une issue"


def test_guardrail_ignores_non_settings_file():
    # La même structure passée avec un autre nom de fichier ne doit rien signaler.
    data = _settings(use_model_knowledge=True, moderation="Medium")
    assert v.find_agent_guardrail_issues(data, "agent.mcs.yml") == []


def test_staging_host_in_prod_flagged():
    data = _http_topic("https://ac360-gateway-staging.azurewebsites.net/api/audit")
    issues = v.find_wiring_issues(data)
    joined = " ".join(str(i).lower() for i in issues)
    assert "staging" in joined or "mort" in joined, (
        "un hôte staging résiduel doit être signalé par find_wiring_issues"
    )


def test_prod_host_passes_wiring():
    data = _http_topic("https://ac360-gateway-prod.azurewebsites.net/api/audit")
    issues = v.find_wiring_issues(data)
    joined = " ".join(str(i).lower() for i in issues)
    assert "staging" not in joined, "l'hôte prod ne doit pas déclencher l'assertion staging"
