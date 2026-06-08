import json
from typing import Optional
import httpx
import jwt
from jwt.algorithms import RSAAlgorithm
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config import load_config
config = load_config()

JWKS_URL = config.jwks_url
API_AUDIENCE = config.client_id
ALLOWED_ISSUERS = [config.issuer]
REQUIRED_SCOPES = config.required_scopes
REQUIRED_ROLES = config.required_roles
from safe_logger import log_security

security = HTTPBearer()

_JWKS_CACHE: Optional[dict] = None

def _fetch_jwks() -> dict:
    global _JWKS_CACHE
    if _JWKS_CACHE is not None:
        return _JWKS_CACHE
    try:
        response = httpx.get(JWKS_URL, timeout=10.0)
        response.raise_for_status()
        _JWKS_CACHE = response.json()
        return _JWKS_CACHE
    except Exception as exc:
        log_security("ERROR", f"Failed to fetch JWKS: {exc}")
        raise HTTPException(
            status_code=503,
            detail="Impossible de télécharger les clés JWKS depuis Microsoft Entra ID."
        )

def _get_public_key(kid: str):
    jwks = _fetch_jwks()
    for key_data in jwks.get("keys", []):
        if key_data.get("kid") == kid:
            return RSAAlgorithm.from_jwk(json.dumps(key_data))
    
    global _JWKS_CACHE
    _JWKS_CACHE = None
    jwks = _fetch_jwks()
    for key_data in jwks.get("keys", []):
        if key_data.get("kid") == kid:
            return RSAAlgorithm.from_jwk(json.dumps(key_data))
    
    log_security("ERROR", f"Public key not found for kid: {kid}")
    raise HTTPException(status_code=401, detail="Clé publique introuvable (kid inconnu).")

def verify_azure_ad_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    token = credentials.credentials

    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.exceptions.DecodeError as exc:
        log_security("ERROR", f"Malformed JWT: {exc}")
        raise HTTPException(status_code=401, detail="Token JWT malformé.")

    kid = unverified_header.get("kid")
    if not kid:
        log_security("ERROR", "Missing kid in JWT header")
        raise HTTPException(status_code=401, detail="Token JWT invalide : champ 'kid' manquant.")

    alg = unverified_header.get("alg", "RS256")
    if alg != "RS256":
        log_security("ERROR", f"Unauthorized algorithm: {alg}")
        raise HTTPException(status_code=401, detail="Algorithme JWT non autorisé. RS256 requis.")

    public_key = _get_public_key(kid)

    try:
        claims = jwt.decode(
            token,
            key=public_key,
            algorithms=["RS256"],
            audience=API_AUDIENCE,
            options={
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iss": True,
                "verify_aud": True,
            }
        )
    except jwt.ExpiredSignatureError:
        log_security("WARNING", "Expired JWT")
        raise HTTPException(status_code=401, detail="Token JWT expiré.")
    except jwt.ImmatureSignatureError:
        log_security("WARNING", "Immature JWT")
        raise HTTPException(status_code=401, detail="Token JWT pas encore valide (nbf).")
    except jwt.InvalidAudienceError:
        log_security("WARNING", "Invalid Audience")
        raise HTTPException(status_code=401, detail="Token JWT : audience invalide.")
    except jwt.PyJWTError as exc:
        log_security("ERROR", f"JWT Validation Error: {exc}")
        raise HTTPException(status_code=401, detail="Token JWT invalide.")

    issuer = claims.get("iss")
    if issuer not in ALLOWED_ISSUERS:
        log_security("ERROR", f"Invalid Issuer: {issuer}")
        raise HTTPException(status_code=401, detail="Token JWT : issuer non autorisé.")

    # Validation Scopes
    if REQUIRED_SCOPES:
        token_scopes = claims.get("scp", "").split(" ")
        for scope in REQUIRED_SCOPES:
            if scope not in token_scopes:
                log_security("WARNING", f"Missing scope: {scope}")
                raise HTTPException(status_code=403, detail=f"Scope manquant : {scope}")

    # Validation Roles
    if REQUIRED_ROLES:
        token_roles = claims.get("roles", [])
        for role in REQUIRED_ROLES:
            if role not in token_roles:
                log_security("WARNING", f"Missing role: {role}")
                raise HTTPException(status_code=403, detail=f"Rôle manquant : {role}")

    upn = claims.get("upn") or claims.get("preferred_username")
    if not upn:
        log_security("ERROR", "No UPN in claims")
        raise HTTPException(status_code=401, detail="Le token ne contient pas d'identité.")

    log_security("INFO", f"Token validated for user: {upn}")
    return upn
