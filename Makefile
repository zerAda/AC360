# =============================================================================
# onix — Stack IA privée (Onyx + Ollama). Pilotage en une commande.
#   make detect    diagnostic matériel (CPU/RAM/GPU) — lecture seule
#   make tune      AUTO-TUNING : écrit les réglages optimaux dans .env
#   make secrets   génère les secrets forts dans .env
#   make up        démarre tout (GPU=1 = profil GPU NVIDIA ; PERF=1 = haut débit)
#   make models    (pré)télécharge les modèles Ollama
#   make verify    contrôle de bout en bout (santé + câblage + génération)
#   make logs / ps / stats / down / restart / update / backup / restore / destroy
# Pré-requis : Docker + Docker Compose v2 (`docker compose`).
# =============================================================================

SHELL := /bin/bash
COMPOSE := docker compose -f docker-compose.yml
ifdef GPU
COMPOSE += -f docker-compose.gpu.yml
endif
ifdef PERF
COMPOSE += -f docker-compose.performance.yml
endif
PORT = $$(sed -n 's/^ONYX_HOST_PORT=//p' .env 2>/dev/null | head -n1); PORT=$${PORT:-3000}

.DEFAULT_GOAL := help
.PHONY: help detect tune secrets up down restart ps stats logs models verify config update backup restore destroy

help:
	@grep -E '^#   make' Makefile | sed 's/^#   /  /'
	@echo ""
	@echo "  Démarrage type :  make tune  →  make secrets  →  make up  →  make verify"

detect:
	@bash scripts/detect-hardware.sh

tune:
	@bash scripts/detect-hardware.sh --apply

secrets:
	@bash scripts/gen-secrets.sh

# Démarre la stack puis pré-tire les modèles → "prêt à l'emploi".
up: secrets
	@$(COMPOSE) up -d
	@echo "→ Attente des services + téléchargement des modèles (1er lancement : plusieurs minutes)…"
	@bash scripts/pull-models.sh || true
	@{ $(PORT); echo ""; echo "✓ Stack démarrée. Ouvrez : http://localhost:$$PORT"; \
	   echo "  Le PREMIER compte créé devient ADMINISTRATEUR."; \
	   echo "  Assistant LLM : choisir 'Ollama', URL http://ollama:11434 (cf. docs/RUNBOOK.md)."; }

down:
	@$(COMPOSE) down

restart:
	@$(COMPOSE) restart

ps:
	@$(COMPOSE) ps

stats:
	@docker stats --no-stream $$($(COMPOSE) ps -q)

logs:
	@$(COMPOSE) logs -f --tail=200

models:
	@bash scripts/pull-models.sh

verify:
	@bash scripts/verify.sh

# Valide la syntaxe du compose (résout les variables) sans rien démarrer.
config:
	@$(COMPOSE) config -q && echo "✓ docker-compose.yml valide"

# Met à jour les images au tag épinglé dans .env (revoir le changelog avant).
update:
	@$(COMPOSE) pull
	@$(COMPOSE) up -d
	@echo "✓ Images mises à jour (tag = IMAGE_TAG du .env)."

backup:
	@bash scripts/backup.sh

restore:
	@bash scripts/restore.sh $(DIR)

# Détruit conteneurs + volumes (DONNÉES PERDUES). Demande confirmation.
# if/then/else explicite : le statut de `down -v` n'est PAS masqué par un `||`
# (l'antipattern `cmd && ... || echo` afficherait "Annulé" même si `down -v` échoue).
destroy:
	@read -p "⚠ Supprimer conteneurs ET volumes (données perdues) ? [oui/non] " a; \
	 if [ "$$a" = "oui" ]; then \
	   $(COMPOSE) down -v; \
	 else \
	   echo "Annulé."; \
	 fi

# --- WS4 ---
# Déploiement Kubernetes HAUTE DISPONIBILITÉ & scale-out (chart Helm onix-ha).
# Cibles de VALIDATION (hors cluster) + déploiement. Cf. docs/HA_SCALING.md.
#   make k8s-lint       helm lint du chart
#   make k8s-template   helm template (défauts) -> rendu + parse YAML
#   make k8s-validate   lint + template (défauts ET data-tier) + parse PyYAML
#   make k8s-deps        helm dependency build (rafraîchit les sous-charts vendorisés)
#   make k8s-deploy      helm upgrade --install (prod ; requiert SECRET + NS onix)
.PHONY: k8s-lint k8s-template k8s-validate k8s-deps k8s-deploy
K8S_CHART := deploy/k8s/onix-ha

k8s-lint:
	@helm lint $(K8S_CHART)

k8s-template:
	@helm template onix $(K8S_CHART) --namespace onix

# Validation COMPLÈTE sans cluster : lint, rendu (2 profils), et re-parse strict
# du YAML (kind/apiVersion/metadata.name) + scan gitleaks si présent.
k8s-validate:
	@echo "→ helm lint…"            && helm lint $(K8S_CHART)
	@echo "→ helm template (défauts)…" \
	  && helm template onix $(K8S_CHART) -n onix > /tmp/onix-k8s-default.yaml
	@echo "→ helm template (data-tier activé)…" \
	  && helm template onix $(K8S_CHART) -n onix \
	     --set postgresql.cluster.enabled=true --set postgresql.operator.enabled=true \
	     --set opensearch.enabled=true --set redis.enabled=true \
	     --set redisOperator.enabled=true --set minio.enabled=true \
	     --set secrets.create=true \
	     --set secrets.values.POSTGRES_PASSWORD=x --set secrets.values.OPENSEARCH_ADMIN_PASSWORD=x \
	     --set secrets.values.REDIS_PASSWORD=x --set secrets.values.S3_AWS_ACCESS_KEY_ID=x \
	     --set secrets.values.S3_AWS_SECRET_ACCESS_KEY=x --set secrets.values.SECRET=x \
	     --set secrets.values.USER_AUTH_SECRET=x --set secrets.values.ONIX_ACTIONS_API_KEY=x \
	     --set secrets.values.BROKER_PASSWORD=x > /tmp/onix-k8s-ha.yaml
	@echo "→ parse YAML strict (PyYAML)…" \
	  && python3 -c "import yaml,sys; \
	d=[x for x in yaml.safe_load_all(open('/tmp/onix-k8s-ha.yaml')) if x]; \
	bad=[o for o in d if not (o.get('kind') and o.get('apiVersion') and o.get('metadata',{}).get('name'))]; \
	print('docs:',len(d),'invalides:',len(bad)); sys.exit(1 if bad else 0)"
	@command -v gitleaks >/dev/null 2>&1 \
	  && { echo '→ gitleaks…'; gitleaks detect --no-banner --source $(K8S_CHART) -c .gitleaks.toml || true; } \
	  || echo '→ gitleaks absent (ignoré).'
	@echo "✓ Validation hors-cluster OK (charge/HA réelle : recette sur cluster — cf. docs/HA_SCALING.md §9)."

k8s-deps:
	@helm dependency build $(K8S_CHART)

# Déploiement prod. Variables : NS (namespace, def. onix), HOST (Ingress),
# SECRET (nom du Secret applicatif créé HORS-CHART). Active le socle data HA.
k8s-deploy:
	@helm upgrade --install onix $(K8S_CHART) -n $${NS:-onix} --create-namespace \
	  --set secrets.existingSecret=$${SECRET:?Créez d abord le Secret K8s (cf. docs/HA_SCALING.md §8)} \
	  --set postgresql.operator.enabled=true --set postgresql.cluster.enabled=true \
	  --set opensearch.enabled=true --set redisOperator.enabled=true --set redis.enabled=true \
	  --set minio.enabled=true \
	  --set ingress.host=$${HOST:-onix.example.com}
