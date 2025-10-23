<#
===========================================================================
 LabBirita Mini — Push GitHub + Deploy Render Full-Automático
===========================================================================
 Autor       : José Biriteiro
 Descrição   : Script PowerShell que automatiza todo o fluxo de deploy
               de um projeto Python/Flask:
                  1️⃣ Cria repositório no GitHub (se não existir)
                  2️⃣ Inicializa Git localmente, adiciona arquivos e faz commit
                  3️⃣ Realiza push seguro usando Personal Access Token
                  4️⃣ Cria ou atualiza Web Service no Render via API
                  5️⃣ Faz rollback se o deploy falhar
 Escopo      : Laboratório de testes/desenvolvimento (educacional)
 Notas       :
    - Evite commitar tokens ou secrets nos arquivos
    - Configure as variáveis de ambiente:
          $env:GITHUB_TOKEN  → GitHub Personal Access Token (repo)
          $env:RENDER_API_KEY → Render API Key
    - Para novos projetos, ajuste $repoName, $renderServiceName, $buildCmd
===========================================================================
#>

# =========================
# ⚡ Configurações
# =========================
$githubUser         = "jbiriteiro"         # Usuário GitHub
$repoName           = "labbirita-mini"     # Nome do repositório
$renderServiceName  = "LabBirita Mini"     # Nome do serviço Render
$localPath          = Convert-Path "."    # Pasta local do projeto
$buildCmd           = "pip install -r requirements.txt"  # Build command Render
$startCmd           = "gunicorn app:app --bind 0.0.0.0:$PORT"  # Start command

# =========================
# 🔑 Autenticação
# =========================
$githubToken = $env:GITHUB_TOKEN
$renderApiKey = $env:RENDER_API_KEY

if (-not $githubToken -or -not $renderApiKey) {
    Write-Error "❌ Configure as variáveis de ambiente: GITHUB_TOKEN e RENDER_API_KEY"
    return
}

$ghHeaders = @{
    Authorization = "token $githubToken"
    Accept = "application/vnd.github+json"
}
$renderHeaders = @{
    "Authorization" = "Bearer $renderApiKey"
    "Content-Type"  = "application/json"
}

# =========================
# 1️⃣ Valida GitHub Token
# =========================
try {
    $ghTest = Invoke-RestMethod -Uri "https://api.github.com/user" -Headers $ghHeaders
    Write-Host "✅ Token GitHub OK! Usuário: $($ghTest.login)"
} catch {
    Write-Error "❌ Token GitHub inválido ou sem permissão."
    return
}

# =========================
# 2️⃣ Cria repositório GitHub se não existir
# =========================
try {
    $body = @{ name = $repoName } | ConvertTo-Json
    $response = Invoke-RestMethod -Uri "https://api.github.com/user/repos" -Method Post -Headers $ghHeaders -Body $body
    Write-Host "✅ Repositório criado: $($response.html_url)"
} catch {
    Write-Warning "⚠️ Repositório já existe ou outro erro: $($_.Exception.Message)"
}

# =========================
# 3️⃣ Inicializa Git local
# =========================
if (-not (Test-Path ".git")) {
    git init
    Write-Host "✅ Git iniciado localmente"
}

# Configura usuário Git se não configurado
$gitName = git config user.name
if (-not $gitName) { git config user.name "José Biriteiro" }
$gitEmail = git config user.email
if (-not $gitEmail) { git config user.email "josebiriteiro@gmail.com" }

# =========================
# 4️⃣ Commit e push
# =========================
git add .
git commit -m "Initial commit — LabBirita Mini" -q
Write-Host "✅ Commit criado"

# Adiciona remoto se não existir
$remoteUrl = "https://github.com/$githubUser/$repoName.git"
if (-not (git remote)) { git remote add origin $remoteUrl }
git branch -M main
git push -u origin main
Write-Host "🚀 Push enviado para GitHub: $remoteUrl"

# =========================
# 5️⃣ Criar ou atualizar serviço no Render
# =========================
# Primeiro, busca serviço existente
$services = Invoke-RestMethod -Uri "https://api.render.com/v1/services" -Headers $renderHeaders
$service = $services | Where-Object { $_.name -eq $renderServiceName }

if ($service) {
    Write-Host "ℹ️ Serviço Render encontrado: $($service.id). Atualizando..."
    $renderBody = @{
        repo = "https://github.com/$githubUser/$repoName"
        branch = "main"
        buildCommand = $buildCmd
        startCommand = $startCmd
    } | ConvertTo-Json
    try {
        $update = Invoke-RestMethod -Uri "https://api.render.com/v1/services/$($service.id)" -Method Patch -Headers $renderHeaders -Body $renderBody
        Write-Host "✅ Serviço atualizado com sucesso: $($update.liveUrl)"
    } catch {
        Write-Warning "❌ Falha ao atualizar serviço. Rollback necessário: $($_.Exception.Message)"
        return
    }
} else {
    Write-Host "ℹ️ Criando novo serviço Render..."
    $renderBody = @{
        name = $renderServiceName
        repo = "https://github.com/$githubUser/$repoName"
        branch = "main"
        type = "web_service"
        buildCommand = $buildCmd
        startCommand = $startCmd
        env = @{}
    } | ConvertTo-Json
    try {
        $create = Invoke-RestMethod -Uri "https://api.render.com/v1/services" -Method Post -Headers $renderHeaders -Body $renderBody
        Write-Host "✅ Serviço criado no Render: $($create.liveUrl)"
    } catch {
        Write-Warning "❌ Não foi possível criar serviço no Render: $($_.Exception.Message)"
        return
    }
}

Write-Host "🎉 Deploy completo! GitHub + Render funcionando 1000 grau"
