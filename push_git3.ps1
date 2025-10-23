# =====================================================
# Push GitHub + Deploy Render Automático
# =====================================================

# ---------- Configurações ----------
$githubUser = "jbiriteiro"        # Seu usuário do GitHub
$repoName = "labbirita-mini"      # Nome do repositório
$localPath = Convert-Path "."     # Pasta local

# Tokens via variável de ambiente (mais seguro)
$env:GITHUB_TOKEN = $env:GITHUB_TOKEN  # Personal Access Token GitHub
$env:RENDER_API_KEY = $env:RENDER_API_KEY  # Render API Key

$githubToken = $env:GITHUB_TOKEN
$renderApiKey = $env:RENDER_API_KEY

# Headers GitHub
$headersGit = @{
    Authorization = "token $githubToken"
    Accept = "application/vnd.github+json"
}

# Headers Render
$headersRender = @{
    Authorization = "Bearer $renderApiKey"
    "Content-Type" = "application/json"
}

# =========================
# 1️⃣ Valida Token GitHub
# =========================
try {
    $user = Invoke-RestMethod -Uri "https://api.github.com/user" -Headers $headersGit
    Write-Host "✅ Token GitHub OK! Usuário autenticado: $($user.login)"
} catch {
    Write-Error "❌ Token GitHub inválido ou sem permissão. Gere um token com escopo 'repo'."
    return
}

# =========================
# 2️⃣ Criar repositório GitHub (se não existir)
# =========================
try {
    $body = @{ name = $repoName } | ConvertTo-Json
    $response = Invoke-RestMethod -Uri "https://api.github.com/user/repos" -Method Post -Headers $headersGit -Body $body
    Write-Host "✅ Repositório criado no GitHub: $($response.html_url)"
} catch {
    Write-Warning "⚠️ Repositório já existe ou houve outro erro: $($_.Exception.Message)"
}

# =========================
# 3️⃣ Inicializa Git local
# =========================
if (-not (Test-Path ".git")) {
    git init
    Write-Host "✅ Git iniciado localmente."
}

# =========================
# 4️⃣ Configura usuário Git (evita erro de commit)
# =========================
git config user.name "José Biriteiro"
git config user.email "josebiriteiro@gmail.com"
Write-Host "✅ Usuário Git configurado."

# =========================
# 5️⃣ Commit dos arquivos
# =========================
git add .
git commit -m "Initial commit — LabBirita Mini"
Write-Host "✅ Commit criado."

# =========================
# 6️⃣ Configura remoto e push
# =========================
$remoteUrl = "https://github.com/$githubUser/$repoName.git"

$remotes = git remote
if ($remotes -notcontains "origin") {
    git remote add origin $remoteUrl
}

git branch -M main
git push -u origin main
Write-Host "✅ Push enviado para GitHub: $remoteUrl"

# =========================
# 7️⃣ Cria Web Service no Render
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
    Write-Host "✅ Deploy Render ativo! URL final: $deployUrl"
} catch {
    Write-Warning "⚠️ Não foi possível criar o serviço no Render: $($_.Exception.Message)"
}