# Sécurité — Stack IA privée AC360 (Onyx + Ollama)

Baseline de sécurité et choix de durcissement. Objectif : un déploiement local
**défendable face à un audit exigeant**, sans réserve laissée ouverte.

## 1. Principes

| Principe | Mise en œuvre |
|---|---|
| Moindre exposition | Un seul port publié, lié à `127.0.0.1`. Tout le reste est interne. |
| Moindre privilège | Auth par comptes locaux ; énumération des comptes réservée aux admins. |
| Pas de secret en clair | Secrets générés localement, `.env` gitignoré + `chmod 600`. |
| Pas de fuite de données | LLM local (Ollama), `DISABLE_TELEMETRY=true`, aucun appel cloud. |
| Surface minimale | Services à risque retirés par défaut (voir §4). |
| Reproductibilité | Images **épinglées** (pas de `latest`), fichier compose unique auditable. |

## 2. Exposition réseau

- **nginx** publie `127.0.0.1:${ONYX_HOST_PORT}:80` → injoignable depuis le LAN/Internet.
- **Ollama** : **aucun** `ports:` → accessible uniquement via le DNS interne
  `ollama:11434`. Le LLM n'est donc jamais exposé hors de la stack.
- Postgres, OpenSearch, MinIO, Redis : **aucun port hôte**. Communication sur le
  réseau Docker privé `ac360-local-ai-net` exclusivement.

> Vérifier : `docker compose ps` ne doit montrer un mapping de port que pour `nginx`,
> et préfixé par `127.0.0.1`.

## 3. Authentification

- `AUTH_TYPE=basic` : comptes email/mot de passe. **Le premier compte créé est admin.**
- `USER_DIRECTORY_ADMIN_ONLY=true` : un non-admin ne peut pas énumérer les comptes.
- `SESSION_EXPIRE_TIME_SECONDS=86400` : ré-authentification quotidienne.
- En accès strictement localhost, la vérification d'email est désactivée (pas de
  SMTP) ; la surface est limitée à la machine. Pour l'activer, voir §6.

## 4. Réduction de la surface d'attaque

Retirés du compose par rapport à la distribution Onyx standard :

| Service | Raison |
|---|---|
| `code-interpreter` | Montait `/var/run/docker.sock` → équivaut à un accès **root sur l'hôte**. Inacceptable par défaut. |
| `certbot` | Inutile en localhost (pas de TLS public). Réintroduit pour un déploiement exposé (§6). |
| `mcp_server` | Surface d'API supplémentaire non requise. |
| 2ᵉ `model_server` (indexing) | Mutualisé avec l'inference server (RAM) ; réactivable pour la montée en charge. |

## 5. Secrets

Générés par `scripts/gen-secrets.sh` (idempotent) :
`SECRET`, `POSTGRES_PASSWORD`, `DB_READONLY_PASSWORD`, `OPENSEARCH_ADMIN_PASSWORD`
(complexité garantie), `MINIO_ROOT_USER/PASSWORD`, `S3_AWS_ACCESS_KEY_ID/SECRET`.

- `.env` est **gitignoré** (`.gitignore` racine) et passé en `chmod 600`.
- **Rotation** : modifier la valeur dans `.env` puis `make up` (certains secrets,
  ex. `OPENSEARCH_ADMIN_PASSWORD`, impliquent une réinitialisation du volume —
  voir RUNBOOK). Conservez les secrets dans un coffre (Key Vault, gestionnaire).
- Le scan `gitleaks` du repo (pre-commit) protège contre un commit accidentel.

## 6. Durcissement pour un déploiement EXPOSÉ (au-delà du localhost)

Si vous devez ouvrir l'accès (serveur partagé) :

1. **TLS obligatoire** — placez un reverse proxy TLS devant nginx (Caddy/Traefik/
   nginx+Let's Encrypt) ou réintroduisez `certbot`. Ne publiez jamais en clair.
2. **Bind** — remplacez `127.0.0.1:` par l'IP voulue, derrière un pare-feu.
3. **SSO** — passez `AUTH_TYPE=oidc` et reliez votre **Entra ID** (cohérent avec
   AC360) : `OPENID_CONFIG_URL`, `OIDC_PKCE_ENABLED=true`, et restreignez avec
   `VALID_EMAIL_DOMAINS=gerep.fr`.
4. **Vérification d'email** (`basic`) — `REQUIRE_EMAIL_VERIFICATION=true` + `SMTP_*`.
5. **Redis** — activez `REDIS_PASSWORD` (interne par défaut, mais défense en profondeur).
6. **Mises à jour** — suivez le changelog Onyx et relevez `IMAGE_TAG` régulièrement.

## 7. Checklist d'acceptation

- [ ] `make verify` : 0 échec.
- [ ] `docker compose ps` : seul `nginx` publie un port, en `127.0.0.1`.
- [ ] `.env` présent, `chmod 600`, secrets non vides, **non** versionné.
- [ ] Aucun mot de passe par défaut (`password`, `minioadmin`, `StrongPassword123!`).
- [ ] `DISABLE_TELEMETRY=true`.
- [ ] Premier compte admin créé avec un mot de passe fort.
- [ ] Sauvegarde testée (`make backup` puis `make restore`).
- [ ] (Si exposé) TLS + SSO + pare-feu en place (§6).
