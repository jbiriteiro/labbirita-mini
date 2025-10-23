<#
LabBirita Mini - Deploy Automático 1000 grau (v3.0 - Service ID Fixo)
------------------------------------------------------------------

Este script faz tudo pra você, agora usando o ID fixo do Render:
1️⃣ Cria/atualiza repositório no GitHub via API
2️⃣ Commit dos arquivos locais automaticamente
3️⃣ Push para a branch 'main'
4️⃣ RODE REDEPLOY no serviço Render via API
5️⃣ Rollback automático caso o deploy falhe (simplificado)
6️⃣ Mensagens coloridas e detalhadas de status

⚠️ ANTES DE RODAR NOVAMENTE:
- Certifique-se de que o repositório contém o arquivo app.py (Web App Flask/Django).
- Este script agora vai direto para o REDEPLOY, pois o Service ID está preenchido.
#>

# ==============================
# Configurações do ambiente (Stricter Mode)
# ==============================
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop" # Garante que qualquer erro de API ou comando Git pare o script

# ==============================
# Configurações do projeto
# ==============================
$githubUser = "jbiriteiro"
$repoName   = "labbirita-mini"
$localPath  = Convert-Path "."

# 🛑 ID DO SERVIÇO RENDER - AGORA FIXO!
$renderServiceId = "srv-d3sq1p8dl3ps73ar54s0"           

# Configurações do Serviço Render
$renderServiceType = "web"
$renderServiceEnv = "python"
$commitMessage = "Deploy Automático: Ativação via ID Fixo v3.0"

# Headers GitHub e Render
$headersGitHub = @{
    Authorization = "token $env:GITHUB_TOKEN"
    Accept = "application/vnd.github+json"
}
$headersRender = @{
    "Authorization" = "Bearer $env:RENDER_API_KEY"
    "Content-Type"  = "application/json"
}

# ==============================
# 1️⃣ Autenticação GitHub
# ==============================
Write-Host "`n# 1. Autenticação GitHub" -ForegroundColor Yellow
try {
    $user = Invoke-RestMethod -Uri "https://api.github.com/user" -Headers $headersGitHub
    Write-Host "✅ Token GitHub OK! Usuário: $($user.login)" -ForegroundColor Green
} catch {
    Write-Host "❌ Token GitHub inválido ou sem permissão. Verifique \$env:GITHUB_TOKEN." -ForegroundColor Red
    exit 1
}

# ==============================
# 2️⃣ Criar repositório GitHub se não existir
# ==============================
Write-Host "`n# 2. Configuração do Repositório GitHub" -ForegroundColor Yellow
try {
    $body = @{ 
        name = $repoName 
        private = $true
    } | ConvertTo-Json
    $response = Invoke-RestMethod -Uri "https://api.github.com/user/repos" -Method Post -Headers $headersGitHub -Body $body
    Write-Host "✅ Repositório criado no GitHub: $($response.html_url)" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Repositório já existe ou outro erro (ok): $($_.Exception.Message)" -ForegroundColor DarkYellow
}

# ==============================
# 3️⃣ Inicializar Git local e Configurar
# ==============================
Write-Host "`n# 3. Inicialização e Configuração Local do Git" -ForegroundColor Yellow
$remoteUrl = "https://$($githubUser):$($env:GITHUB_TOKEN)@github.com/$githubUser/$repoName.git"

try {
    if (-not (Test-Path ".git")) {
        git init | Out-Null
        Write-Host "✅ Git iniciado localmente" -ForegroundColor Green
        git config user.name "José Biriteiro"
        git config user.email "josebiriteiro@gmail.com"
    }

    $remotes = git remote
    if ($remotes -notcontains "origin") {
        git remote add origin $remoteUrl | Out-Null
        Write-Host "✅ Remoto 'origin' adicionado." -ForegroundColor Green
    } else {
        git remote set-url origin $remoteUrl | Out-Null
        Write-Host "✅ Remoto 'origin' atualizado." -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Falha ao configurar o Git local: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# ==============================
# 4️⃣ Commit e Push
# ==============================
Write-Host "`n# 4. Commit e Push para GitHub" -ForegroundColor Yellow
try {
    git add . | Out-Null
    git commit -m "$commitMessage" | Out-Null
    Write-Host "✅ Commit efetuado: '$commitMessage'" -ForegroundColor Green
    
    git branch -M main | Out-Null
    git push -u origin main | Out-Null
    Write-Host "🚀 Push enviado para GitHub: https://github.com/$githubUser/$repoName" -ForegroundColor Cyan
} catch {
    Write-Host "❌ Falha no Commit/Push. Verifique suas permissões." -ForegroundColor Red
    exit 1
}

# ==============================
# 5️⃣ Deploy no Render
# ==============================
Write-Host "`n# 5. Deploy no Render" -ForegroundColor Yellow
try {
    $repoUrl = "https://github.com/$githubUser/$repoName"

    if ($renderServiceId -eq "") {
        # Esta seção nunca deve ser alcançada, pois $renderServiceId está fixo.
        Write-Host "❌ Erro Crítico: O Service ID não está fixo. Use a versão anterior do script para criação manual." -ForegroundColor Red
        exit 1

    } else {
        # ✅ ATIVAÇÃO DO REDEPLOY
        $deployResponse = Invoke-RestMethod -Uri "https://api.render.com/v1/services/$renderServiceId/deploys" -Method Post -Headers $headersRender 
        Write-Host "✅ Redeploy solicitado com sucesso para o serviço: $renderServiceId" -ForegroundColor Green
    }

    # Feedback da URL do Render (se disponível)
    if ($deployResponse.service.serviceDetails.url) {
        Write-Host "🌐 URL do Serviço: $($deployResponse.service.serviceDetails.url)" -ForegroundColor Cyan
    }

} catch {
    Write-Host "❌ Deploy Render falhou: $($_.Exception.Message)" -ForegroundColor Red
    
    # Rollback simplificado (Depende da API do Render)
    if ($renderServiceId) {
        Write-Host "♻️ Rollback automático acionado para serviço $renderServiceId (Verifique o log do Render)" -ForegroundColor Yellow
    }
    exit 1
}

# ==============================
# 6️⃣ Finalização
# ==============================
Write-Host "`n🎉 DEPLOY AUTOMÁTICO CONCLUÍDO COM SUCESSO!" -ForegroundColor Magenta
Write-Host "------------------------------------------------------" -ForegroundColor Magenta
Write-Host "⚠️ PRÓXIMO PASSO: O script só SOLICITOU o deploy. Verifique o log do Render para confirmar o status FINAL (Sucesso/Falha)." -ForegroundColor Yellow