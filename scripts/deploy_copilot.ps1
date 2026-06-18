<#
.SYNOPSIS
  Deploy the AC360 Copilot Studio agent (src/copilot/AC360) to a Power Platform environment.

.DESCRIPTION
  The agent is stored as a pac "copilot agent workspace" (loose .mcs.yml source), NOT a packaged
  Dataverse solution. Therefore it is deployed with `pac copilot push` (direct) or `pac copilot pack`
  + `pac solution import` (solution route) — NEVER with `pac solution import` against the raw folder
  (that throws "solution file is invalid / missing solution.xml").

  This script: validates pac auth + the target env, checks the prod gateway is live, runs the offline
  guardrail gate, then deploys. The UI-only finishing steps (connection rebind, action endpoint/audience,
  manual Entra V2 SSO, publish, 1:1 Teams install) cannot be scripted and are printed as a checklist.

.PARAMETER EnvUrl
  Target prod Dataverse environment URL (e.g. https://orgXXXX.crm4.dynamics.com) or its GUID.
  If omitted, the active pac auth profile's org is used.

.PARAMETER Mode
  Push  = `pac copilot push` (direct deploy of the workspace — simplest). Default.
  Pack  = `pac copilot pack` -> `pac solution import` (solution/ALM route).

.PARAMETER GatewayUrl
  Prod gateway base URL the agent's actions call. Default: https://ac360-gateway-prod.azurewebsites.net

.EXAMPLE
  pwsh scripts/deploy_copilot.ps1 -EnvUrl "https://orgXXXX.crm4.dynamics.com" -Mode Push
#>
[CmdletBinding()]
param(
    [string]$EnvUrl,
    [ValidateSet('Push', 'Pack')]
    [string]$Mode = 'Push',
    [string]$PublisherPrefix = 'cra7f',
    [string]$SolutionName = 'AC360Agent',
    [string]$GatewayUrl = 'https://ac360-gateway-prod.azurewebsites.net'
)

$ErrorActionPreference = 'Stop'
$RepoRoot   = Split-Path $PSScriptRoot -Parent
$ProjectDir = Join-Path $RepoRoot 'src/copilot/AC360'
$OutZip     = Join-Path $RepoRoot ("out/{0}.zip" -f $SolutionName)

function Step($n, $msg) { Write-Host "`n=== [$n] $msg ===" -ForegroundColor Cyan }
function Fail($msg) { Write-Host "FAIL: $msg" -ForegroundColor Red; exit 1 }

# --- 0. Tooling -------------------------------------------------------------
Step 0 'Power Platform CLI present'
if (-not (Get-Command pac -ErrorAction SilentlyContinue)) {
    Fail "pac CLI not found. Install: 'dotnet tool install --global Microsoft.PowerApps.CLI.Tool' (or 'pac install latest')."
}
pac --version

# --- 1. Auth + target environment ------------------------------------------
Step 1 'Authenticate to the target environment'
if ($EnvUrl) {
    # Creates/refreshes an auth profile bound to the prod env (interactive sign-in as your admin).
    pac auth create --environment $EnvUrl
}
Write-Host '--- active auth profiles ---'
pac auth list
Write-Host '--- active organization ---'
pac org who
Write-Host "Confirm the org above is your EU PROD environment before continuing." -ForegroundColor Yellow

# --- 2. Prereq: prod gateway must be live (or every audit action 401s) ------
Step 2 "Prod gateway health ($GatewayUrl/health)"
try {
    $h = Invoke-WebRequest -Uri "$GatewayUrl/health" -UseBasicParsing -TimeoutSec 20
    if ($h.StatusCode -eq 200) { Write-Host "gateway /health = 200 OK" -ForegroundColor Green }
    else { Write-Host "gateway /health = $($h.StatusCode) (expected 200)" -ForegroundColor Yellow }
} catch {
    Write-Host "WARNING: gateway $GatewayUrl/health not reachable. Deploy the Azure backend FIRST" -ForegroundColor Yellow
    Write-Host "(GitHub Actions cd-prod.yml, or scripts/provision.ps1 -> runbook docs/production/runbooks/01-deploy.md)." -ForegroundColor Yellow
    Write-Host "The agent will import, but audit actions will fail until the gateway answers." -ForegroundColor Yellow
}

# --- 3. Offline guardrail gate (PUB-04) ------------------------------------
Step 3 'Guardrail validation (useModelKnowledge=false, High moderation, no staging host)'
python "$RepoRoot/scripts/validate_copilot_yaml.py"
if ($LASTEXITCODE -ne 0) { Fail "validate_copilot_yaml.py failed (exit $LASTEXITCODE). Fix guardrails before deploying." }

# --- 4. Deploy --------------------------------------------------------------
Step 4 "Deploy agent ($Mode)"
if ($Mode -eq 'Push') {
    # Direct push of the workspace into the active env.
    pac copilot push --project-dir $ProjectDir
}
else {
    New-Item -ItemType Directory -Force (Split-Path $OutZip -Parent) | Out-Null
    pac copilot pack --publisher-prefix $PublisherPrefix --solution-name $SolutionName --project-dir $ProjectDir --output-path $OutZip
    if ($LASTEXITCODE -ne 0) { Fail "pac copilot pack failed (exit $LASTEXITCODE)." }
    pac solution import --path $OutZip --activate-plugins --publish-changes
}
if ($LASTEXITCODE -ne 0) { Fail "Deploy failed (exit $LASTEXITCODE)." }
Write-Host "Agent components deployed to the environment." -ForegroundColor Green

# --- 5. Manual finishing steps (UI-only — cannot be scripted) ---------------
Step 5 'MANUAL steps in Copilot Studio (required — or the agent silently 401s)'
@"
  1. Rebind the 3 CONNECTION REFERENCES (src/copilot/AC360/connectionreferences.mcs.yml:
       shared_a365copilotchatmcp, shared_a365memcp, shared_workiqsharepoint) to PROD connections.
  2. Action ENDPOINT  -> $GatewayUrl
     API AUDIENCE/scope -> api://<prod-api-app-id>/Audit.Trigger   (Phase-2 app-reg output)
  3. Settings > Security > Authentication = 'Authenticate manually (Microsoft Entra ID V2)'
       NOT 'Authenticate with Microsoft' (that hides System.User.AccessToken -> every call 401s).
       Require sign-in = ON. Configure Teams SSO. Then REPUBLISH.
  4. Channels > Teams: PERSONAL (1:1) scope only; team/channel scope OFF (OBO + SharePoint RAG need 1:1).
  5. TEST: 1:1 sign-in (no repeat prompts) | grounded SharePoint search | a known-blocked prompt is BLOCKED.
  Full procedure: docs/production/runbooks/06-copilot-publish.md
"@ | Write-Host -ForegroundColor White
