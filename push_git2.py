# =====================================================
# Push GitHub + Deploy no Render (PowerShell)
# =====================================================

# ⚡ Configurações iniciais
$githubUser = "jbiriteiro"         # Seu usuário GitHub
$repoName   = "labbirita-mini"     # Nome do repositório
$token      = $env:GITHUB_TOKEN    # Token do GitHub (setado no PowerShell)
$renderApiKey = "rnd_sm1TlJ5y9jWEWC7MePXJlIigCHHk"  # API Key do Render

# Pasta local
$localPath = Convert-Path "."

# Headers GitHub
$ghHeaders = @{
    Authorization = "token $token"
    Accept = "application/vnd.github+json"
}

# =========================
# 1️⃣ Valida GitHub Token
# =========================
try {
    $test = Invoke-RestMethod -Uri "https://api.github.com/user" -Headers $ghHeaders
    Write-Host "✅ GitHub Token OK! Usuário: $($test.login)"
} catch {
    Write-Error "❌ Token GitHub inválido ou sem permissão. Gere um novo token com escopo 'repo'."
    return
}

# =========================
# 2️⃣ Cria repositório no GitHub se não existir
# =========================
try {
    $body = @{ name = $repoName } | ConvertTo-Json
    $response = Invoke-RestMethod -Uri "https://api.github.com/user/repos" -Method Post -Headers $ghHeaders -Body $body
    Write-Host "✅ Repositório criado: $($response.html_url)"
} catch {
    Write-Warning "⚠️ Repositório já existe ou outro erro: $($_.Exception.Message)"
}

# =========================
# 3️⃣ Inicializa Git local se necessário
# =========================
if (-not (Test-Path ".git")) {
    git init
    Write-Host "✅ Git iniciado localmente."
}

# =========================
# 4️⃣ Configura usuário Git (se não configurado)
# =========================
try {
    $name = git config user.name
    $email = git config user.email
    if (-not $name) { git config user.name "José Biriteiro" }
    if (-not $email) { git config user.email "josebiriteiro@gmail.com" }
    Write-Host "✅ Usuário Git configurado."
} catch {
    git config user.name "José Biriteiro"
    git config user.email "josebiriteiro@gmail.com"
}

# =========================
# 5️⃣ Commit dos arquivos
# =========================
git add .
git commit -m "Initial commit — LabBirita Mini"
Write-Host "✅ Commit criado."

# =========================
# 6️⃣ Adiciona remoto e push
# =========================
$remoteUrl = "https://$githubUser@$token@github.com/$githubUser/$repoName.git"
$remotes = git remote
if ($remotes -notcontains "origin") {
    git remote add origin $remoteUrl
}
git branch -M main
git push -u origin main
Write-Host "🚀 Código enviado para GitHub: https://github.com/$githubUser/$repoName"

# =========================
# 7️⃣ Deploy automático no Render
# =========================
# ⚠️ Antes, crie um Web Service manualmente no Render com esse repo
# e copie o ID do serviço. Substitua abaixo:
$renderServiceId = "COLE_ID_DO_SERVICO_AQUI"

$renderHeaders = @{
    Authorization = "Bearer $renderApiKey"
    "Content-Type" = "application/json"
}

$body = @{ "message" = "Deploy automático via PowerShell" } | ConvertTo-Json

try {
    $deploy = Invoke-RestMethod -Uri "https://api.render.com/v1/services/$renderServiceId/deploys" `
        -Method Post -Headers $renderHeaders -Body $body
    Write-Host "✅ Deploy disparado no Render! ID do deploy: $($deploy.id)"
} catch {
    Write-Warning "⚠️ Não foi possível disparar deploy no Render: $($_.Exception.Message)"
}

Write-Host "🔥 Tudo pronto! Abra sua loja online e teste: https://$repoName.onrender.com"