# =====================================================
# Push GitHub + Deploy Render Automático (Turbo CI/CD)
# =====================================================

# ---------- Configurações ----------
$githubUser = "jbiriteiro"        # Seu usuário GitHub
$repoName = "labbirita-mini"      # Nome do repositório
$localPath = Convert-Path "."

# Tokens via variável de ambiente
$githubToken = $env:GITHUB_TOKEN
$renderApiKey = $env:RENDER_API_KEY

if (-not $githubToken) { Write-Error "❌ Configure GITHUB_TOKEN"; return }
if (-not $renderApiKey) { Write-Error "❌ Configure RENDER_API_KEY"; return }

# Headers
$headersGit = @{
    Authorization = "token $githubToken"
    Accept = "application/vnd.github+json"
}
$headersRender = @{
    Authorization = "Bearer $renderApiKey"
    "Content-Type" = "application/json"
}

# =========================
# 1️⃣ Valida Token GitHub
# =========================
try {
    $user = Invoke-RestMethod -Uri "https://api.github.com/user" -Headers $headersGit
    Write-Host "✅ Token GitHub OK! Usuário: $($user.login)"
} catch { Write-Error "❌ Token GitHub inválido ou sem permissão"; return }

# =========================
# 2️⃣ Cria repositório GitHub (se não existir)
# =========================
try {
    $body = @{ name = $repoName } | ConvertTo-Json
    Invoke-RestMethod -Uri "https://api.github.com/user/repos" -Method Post -Headers $headersGit -Body $body
    Write-Host "✅ Repositório criado no GitHub"
} catch { Write-Warning "⚠️ Repositório já existe ou outro erro" }

# =========================
# 3️⃣ Inicializa Git local
# =========================
if (-not (Test-Path ".git")) { git init; Write-Host "✅ Git iniciado localmente" }

# =========================
# 4️⃣ Configura usuário Git
# =========================
git config user.name "José Biriteiro"
git config user.email "josebiriteiro@gmail.com"
Write-Host "✅ Usuário Git configurado"

# =========================
# 5️⃣ Detecta mudanças
# =========================
$changes = git status --porcelain
if (-not $changes) {
    Write-Host "ℹ️ Nenhuma alteração detectada. Push e deploy não necessários."
    return
}

# =========================
# 6️⃣ Commit incremental
# =========================
git add .
git commit -m "Atualização automática — LabBirita Mini"
Write-Host "✅ Commit criado"

# =========================
# 7️⃣ Push GitHub
# =========================
$remoteUrl = "https://github.com/$githubUser/$repoName.git"
if (-not (git remote)) { git remote add origin $remoteUrl }
git branch -M main
git push -u origin main
Write-Host "✅ Push enviado para GitHub: $remoteUrl"

# =========================
# 8️⃣ Deploy Render
# =========================
$bodyRender = @{
    name = $repoName
    type = "web_service"
    plan = "free"
    repo = @{
        name = $repoName
        branch = "main"
        provider = "github"
    }
    envVars = @()
} | ConvertTo-Json -Depth 5

try {
    $renderResp = Invoke-RestMethod -Uri "https://api.render.com/v1/services" -Method Post -Headers $headersRender -Body $bodyRender
    $deployUrl = $renderResp.serviceDetails.serviceURL
    Write-Host "🚀 Deploy Render ativo! URL final: $deployUrl"
} catch {
    Write-Warning "⚠️ Não foi possível criar/atualizar o serviço no Render: $($_.Exception.Message)"
}