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

# =============================================================================
# --- WS3 --- Déploiement de PRODUCTION (TLS Caddy + OIDC Entra ID + multi-env)
# -----------------------------------------------------------------------------
# Schéma multi-environnement : un fichier .env PAR environnement.
#   ENV=.env                      (dev / local — défaut, profil basic 127.0.0.1)
#   ENV=deploy/prod/.env.test     (test / pré-prod)
#   ENV=deploy/prod/.env.prod     (production)
# La surcouche prod s'EMPILE sur la base : reverse-proxy TLS, OIDC forcé, nginx
# repassé en interne, garde-fou « défaut-sûr » (refuse une expo sans TLS+OIDC).
#
#   make config-prod   valide la composition base + prod (syntaxe, défaut ENV=.env)
#   make up-prod       démarre la stack de PRODUCTION (base + surcouche prod)
#   make down-prod / logs-prod / ps-prod     exploitation prod
#   make secrets-prod  génère les secrets dans le .env ciblé (ENV=…)
# Démarrage type prod :
#   cp deploy/prod/env.prod.template deploy/prod/.env.prod   # puis renseigner
#   make secrets-prod ENV=deploy/prod/.env.prod
#   make up-prod      ENV=deploy/prod/.env.prod
# =============================================================================
ENV ?= .env
COMPOSE_PROD := docker compose --env-file $(ENV) -f docker-compose.yml -f deploy/prod/docker-compose.prod.yml

.PHONY: config-prod up-prod down-prod restart-prod ps-prod logs-prod secrets-prod preflight-prod

# Valide la composition (résout les variables) sans rien démarrer.
config-prod:
	@$(COMPOSE_PROD) config -q && echo "✓ base + prod valide (ENV=$(ENV))"

# Génère/complète les secrets dans le fichier d'environnement ciblé.
secrets-prod:
	@ENV_FILE=$(ENV) bash scripts/gen-secrets.sh

# Démarre la stack de production (base + surcouche TLS/OIDC). Le service
# `preflight` refuse de démarrer une exposition sans TLS+OIDC+vérif. e-mail.
up-prod:
	@$(COMPOSE_PROD) up -d
	@echo "→ Stack PROD démarrée (ENV=$(ENV)). Caddy obtient le certificat TLS au 1er accès."
	@D=$$(sed -n 's/^ONYX_DOMAIN=//p' $(ENV) 2>/dev/null | head -n1); \
	  echo "  Ouvrez : https://$${D:-<ONYX_DOMAIN>}  (SSO Entra ID)."; \
	  echo "  Callback à déclarer côté Entra ID : https://$${D:-<ONYX_DOMAIN>}/auth/oidc/callback"

down-prod:
	@$(COMPOSE_PROD) down

restart-prod:
	@$(COMPOSE_PROD) restart

ps-prod:
	@$(COMPOSE_PROD) ps

logs-prod:
	@$(COMPOSE_PROD) logs -f --tail=200

# Exécute le garde-fou de défaut-sûr seul (diagnostic), avec l'environnement ciblé.
preflight-prod:
	@set -a; . ./$(ENV) 2>/dev/null || true; set +a; sh scripts/preflight-prod.sh
