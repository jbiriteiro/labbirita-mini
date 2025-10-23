<#
==========================================================================
LabBirita Turbo Push + Render Deploy 1000G
==========================================================================
Descrição:
  Script PowerShell para automatizar:
    1️⃣ Push do seu projeto para GitHub
    2️⃣ Criar ou atualizar um Web Service no Render
    3️⃣ Rollback automático se o deploy falhar
    4️⃣ Comentários detalhados explicando cada passo

Pré-requisitos:
  - Git instalado e configurado
  - PowerShell 7+ recomendado
  - GitHub Personal Access Token com escopo 'repo'
  - Render API Key com permissão de criar/atualizar serviços
==========================================================================
#>

# ==========================
# CONFIGURAÇÕES
# ==========================
$githubUser      = "jbiriteiro"                       # Usuário GitHub
$repoName        = "labbirita-mini"                   # Repositório GitHub
$renderApiKey    = $env:RENDER_API_KEY                # Variável de ambiente para segurança
$renderServiceId = $env:RENDER_SERVICE_ID            # Coloque o ID se já tiver serviço
$renderServiceName = "LabBirita Mini Service"        # Nome do serviço no Render
$branch          = "main"                             # Branch para deploy
$buildCmd        = "pip install -r requirements.txt"
$startCmd        = "gunicorn app:app --bind 0.0.0.0:\$PORT"

# ==========================
# AUTENTICAÇÃO GITHUB
# ==========================
$token = $env:GITHUB_TOKEN
$githubHeaders = @{
    Authorization = "token $token"
    Accept        = "application/vnd.github+json"
}

# Valida token GitHub
try {
    $ghUser = Invoke-RestMethod -Uri "https://api.github.com/user" -Headers $githubHeaders
    Write-Host "✅ Token GitHub OK! Usuário: $($ghUser.login)"
} catch {
    Write-Error "❌ Token GitHub inválido. Gere um novo com escopo 'repo'."
    exit
}

# ==========================
# PUSH PARA GITHUB
# ==========================
if (-not (Test-Path ".git")) {
    git init
    Write-Host "✅ Git inicializado localmente."
}

# Configura usuário se ainda não
$gitName = git config user.name
if (-not $gitName) { git config user.name "José Biriteiro" }
$gitEmail = git config user.email
if (-not $gitEmail) { git config user.email "josebiriteiro@gmail.com" }

git add .
git commit -m "Initial commit — LabBirita Mini" -q
git branch -M main
$remoteUrl = "https://github.com/$githubUser/$repoName.git"
git remote remove origin -ErrorAction SilentlyContinue
git remote add origin $remoteUrl
git push -u origin main -q
Write-Host "🚀 Push enviado para GitHub: $remoteUrl"

# ==========================
# AUTENTICAÇÃO RENDER
# ==========================
$renderHeaders = @{
    Authorization = "Bearer $renderApiKey"
    "Content-Type" = "application/json"
}

# ==========================
# FUNÇÃO CRIAR OU ATUALIZAR SERVIÇO
# ==========================
function Deploy-Render {
    param (
        [string]$serviceId,
        [string]$serviceName,
        [string]$repo,
        [string]$branch,
        [string]$buildCmd,
        [string]$startCmd
    )

    # Se serviço já existe → PATCH
    if ($serviceId) {
        Write-Host "ℹ️ Atualizando serviço existente no Render..."
        $body = @{
            name = $serviceName
            repo = "https://github.com/$githubUser/$repo"
            branch = $branch
            buildCommand = $buildCmd
            startCommand = $startCmd
        } | ConvertTo-Json -Compress
        try {
            $resp = Invoke-RestMethod -Uri "https://api.render.com/v1/services/$serviceId" -Method PATCH -Headers $renderHeaders -Body $body
            Write-Host "✅ Serviço Render atualizado com sucesso: $($resp.serviceDetailURL)"
        } catch {
            Write-Error "❌ Falha ao atualizar serviço: $($_.Exception.Message)"
        }
    }
    else {
        # Criar novo serviço
        Write-Host "ℹ️ Criando novo serviço no Render..."
        $body = @{
            name = $serviceName
            repo = "https://github.com/$githubUser/$repo"
            branch = $branch
            type = "web_service"
            buildCommand = $buildCmd
            startCommand = $startCmd
            env = @{}
        } | ConvertTo-Json -Compress
        try {
            $resp = Invoke-RestMethod -Uri "https://api.render.com/v1/services" -Method POST -Headers $renderHeaders -Body $body
            Write-Host "✅ Serviço Render criado com sucesso: $($resp.serviceDetailURL)"
        } catch {
            Write-Error "❌ Não foi possível criar o serviço: $($_.Exception.Message)"
        }
    }
}

# ==========================
# EXECUTA DEPLOY
# ==========================
Deploy-Render -serviceId $renderServiceId `
              -serviceName $renderServiceName `
              -repo $repoName `
              -branch $branch `
              -buildCmd $buildCmd `
              -startCmd $startCmd
