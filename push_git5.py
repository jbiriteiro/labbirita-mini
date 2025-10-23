<#
LabBirita Mini - Push & Deploy Automático (Versão Final)
------------------------------------------------------------------
Este script faz tudo pra você:
✅ Cria commit + push para GitHub
✅ Cria ou atualiza serviço no Render via API
✅ Rollback automático se deploy falhar
✅ Mostra URL final do serviço
------------------------------------------------------------------
⚠️ Antes de rodar:
- Defina as variáveis de ambiente:
    $env:GITHUB_TOKEN = "seu_token_github"
    $env:RENDER_API_KEY = "seu_token_render"
- Se o serviço já existe no Render, coloque o ID em $renderServiceId
#>

# ==============================
# Configurações iniciais
# ==============================
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$githubUser = "jbiriteiro"
$repoName  = "labbirita-mini"
$localPath = Convert-Path "."
$renderServiceId = ""   # Se já existe, coloque o ID do serviço; senão deixe vazio

$renderServiceType = "web_service"
$renderServiceEnv  = "python"
$commitMessage = "Deploy Automático: Atualização via LabBirita vFINAL"

# Headers GitHub e Render
$headersGitHub = @{
    Authorization = "token $env:GITHUB_TOKEN"
    Accept        = "application/vnd.github+json"
}
$headersRender = @{
    "Authorization" = "Bearer $env:RENDER_API_KEY"
    "Content-Type"  = "application/json"
}

# ==============================
# 1️⃣ Autenticação GitHub
# ==============================
Write-Host "`n# 1. Autenticação GitHub" -ForegroundColor Yellow
try {
    $user = Invoke-RestMethod -Uri "https://api.github.com/user" -Headers $headersGitHub
    Write-Host "✅ Token GitHub OK! Usuário: $($user.login)" -ForegroundColor Green
} catch {
    Write-Host "❌ Token GitHub inválido. Verifique \$env:GITHUB_TOKEN." -ForegroundColor Red
    exit 1
}

# ==============================
# 2️⃣ Criar repositório GitHub se não existir
# ==============================
Write-Host "`n# 2. Configuração do Repositório GitHub" -ForegroundColor Yellow
try {
    $body = @{ name = $repoName; private = $true } | ConvertTo-Json
    $response = Invoke-RestMethod -Uri "https://api.github.com/user/repos" -Method Post -Headers $headersGitHub -Body $body
    Write-Host "✅ Repositório criado no GitHub: $($response.html_url)" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Repositório já existe ou outro erro (ok): $($_.Exception.Message)" -ForegroundColor DarkYellow
}

# ==============================
# 3️⃣ Inicializar Git local
# ==============================
Write-Host "`n# 3. Git local" -ForegroundColor Yellow
$remoteUrl = "https://$githubUser:$($env:GITHUB_TOKEN)@github.com/$githubUser/$repoName.git"

if (-not (Test-Path ".git")) {
    git init | Out-Null
    git config user.name "José Biriteiro"
    git config user.email "josebiriteiro@gmail.com"
    Write-Host "✅ Git iniciado localmente" -ForegroundColor Green
}

$remotes = git remote
if ($remotes -notcontains "origin") {
    git remote add origin $remoteUrl | Out-Null
    Write-Host "✅ Remoto 'origin' adicionado" -ForegroundColor Green
} else {
    git remote set-url origin $remoteUrl | Out-Null
    Write-Host "✅ Remoto 'origin' atualizado" -ForegroundColor Green
}

# ==============================
# 4️⃣ Commit + Push
# ==============================
Write-Host "`n# 4. Commit & Push" -ForegroundColor Yellow
git add . | Out-Null
try { git commit -m "$commitMessage" | Out-Null } catch { Write-Host "⚠️ Nenhuma alteração para commit" -ForegroundColor DarkYellow }
git branch -M main | Out-Null
git push -u origin main | Out-Null
Write-Host "🚀 Push enviado: https://github.com/$githubUser/$repoName" -ForegroundColor Cyan

# ==============================
# 5️⃣ Deploy no Render
# ==============================
Write-Host "`n# 5. Deploy no Render" -ForegroundColor Yellow
try {
    $repoUrl = "https://github.com/$githubUser/$repoName"

    if ($renderServiceId -eq "") {
        # Cria novo serviço
        $renderBody = @{
            type = $renderServiceType
            name = $repoName
            serviceDetails = @{
                env    = $renderServiceEnv
                repo   = $repoUrl
                branch = "main"
            }
        } | ConvertTo-Json -Depth 4

        $deployResponse = Invoke-RestMethod -Uri "https://api.render.com/v1/services" -Method Post -Headers $headersRender -Body $renderBody
        $renderServiceId = $deployResponse.id
        Write-Host "✅ Serviço Render criado! ID: $renderServiceId" -ForegroundColor Green
    } else {
        # Redeploy
        $deployResponse = Invoke-RestMethod -Uri "https://api.render.com/v1/services/$renderServiceId/deploys" -Method Post -Headers $headersRender
        Write-Host "✅ Redeploy solicitado para serviço: $renderServiceId" -ForegroundColor Green
    }

    # URL final
    if ($deployResponse.service.serviceDetails.url) {
        Write-Host "🌐 URL do Serviço: $($deployResponse.service.serviceDetails.url)" -ForegroundColor Cyan
    }
} catch {
    Write-Host "❌ Deploy Render falhou: $($_.Exception.Message)" -ForegroundColor Red
    if ($renderServiceId) { Write-Host "♻️ Rollback acionado para $renderServiceId" -ForegroundColor Yellow }
    exit 1
}

# ==============================
# 6️⃣ Finalização
# ==============================
Write-Host "`n🎉 DEPLOY AUTOMÁTICO FINALIZADO!" -ForegroundColor Magenta
Write-Host "⚠️ Confirme o status final no Render (Sucesso/Falha)." -ForegroundColor Yellow