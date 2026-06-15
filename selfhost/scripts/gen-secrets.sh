#!/usr/bin/env bash
# =============================================================================
# Génère des secrets forts dans .env (idempotent : ne réécrit jamais un secret
# déjà défini, pour ne pas casser une stack en cours). Crée .env depuis le
# gabarit si absent, puis verrouille les permissions (chmod 600).
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."

ENV_FILE=".env"
TEMPLATE="env.template"

if [ ! -f "$ENV_FILE" ]; then
  cp "$TEMPLATE" "$ENV_FILE"
  echo "→ $ENV_FILE créé depuis $TEMPLATE"
fi

# Génère une chaîne alphanumérique de N caractères.
rand() {
  local n="${1:-32}"
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -base64 $((n * 2)) | tr -dc 'A-Za-z0-9' | head -c "$n"
  else
    LC_ALL=C tr -dc 'A-Za-z0-9' < /dev/urandom | head -c "$n"
  fi
}
gen_user() { printf 'onyx_%s' "$(rand 12)"; }
# OpenSearch exige une complexité (maj/min/chiffre/spécial) : on garantit les classes.
gen_os_pass() { printf '%sAa9!' "$(rand 24)"; }

get_val() { sed -n "s/^$1=//p" "$ENV_FILE" | head -n1; }

set_val() {
  local key="$1" val="$2"
  if grep -q "^$key=" "$ENV_FILE"; then
    awk -v k="$key" -v v="$val" -F= '$1==k{print k"="v; next}{print}' \
      "$ENV_FILE" > "$ENV_FILE.tmp" && mv "$ENV_FILE.tmp" "$ENV_FILE"
  else
    printf '%s=%s\n' "$key" "$val" >> "$ENV_FILE"
  fi
}

ensure() { # ensure KEY GENERATOR [ARGS...]
  local key="$1"; shift
  if [ -z "$(get_val "$key")" ]; then
    set_val "$key" "$("$@")"
    echo "  + $key généré"
  else
    echo "  = $key déjà défini (inchangé)"
  fi
}

echo "Génération des secrets dans $ENV_FILE :"
ensure SECRET                rand 48
ensure POSTGRES_PASSWORD     rand 32
ensure DB_READONLY_PASSWORD  rand 32
ensure OPENSEARCH_ADMIN_PASSWORD gen_os_pass
ensure MINIO_ROOT_USER       gen_user
ensure MINIO_ROOT_PASSWORD   rand 32

# Les identifiants S3 d'Onyx pointent sur le compte root MinIO (mêmes valeurs).
if [ -z "$(get_val S3_AWS_ACCESS_KEY_ID)" ]; then
  set_val S3_AWS_ACCESS_KEY_ID "$(get_val MINIO_ROOT_USER)"; echo "  + S3_AWS_ACCESS_KEY_ID = MINIO_ROOT_USER"
fi
if [ -z "$(get_val S3_AWS_SECRET_ACCESS_KEY)" ]; then
  set_val S3_AWS_SECRET_ACCESS_KEY "$(get_val MINIO_ROOT_PASSWORD)"; echo "  + S3_AWS_SECRET_ACCESS_KEY = MINIO_ROOT_PASSWORD"
fi

chmod 600 "$ENV_FILE"
echo "✓ Secrets prêts. Permissions $ENV_FILE → 600 (lecture/écriture propriétaire uniquement)."
echo "  Sauvegardez ces secrets dans votre coffre (ex: Azure Key Vault / gestionnaire de mots de passe)."
