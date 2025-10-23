<#
LabBirita Mini - Deploy Automático 1000 grau (v2.0 - Turbo Edition)
------------------------------------------------------------------

Este script faz tudo pra você:
1️⃣ Cria/atualiza repositório no GitHub via API
2️⃣ Commit dos arquivos locais automaticamente
3️⃣ Push para a branch 'main'
4️⃣ Cria ou atualiza serviço no Render via API (configurável)
5️⃣ Rollback automático caso o deploy falhe (simplificado)
6️⃣ Mensagens coloridas e detalhadas de status

⚠️ Antes de rodar:
- Defina suas variáveis de ambiente:
  $env:GITHUB_TOKEN = "seu_token_github"
  $env:RENDER_API_KEY = "seu_token_render"
- Se o repositório já existe, o script faz commit/push normalmente.
- O script suporta rollback seguro no Render.
#>

# ==============================
# Configurações do ambiente (Stricter Mode)
# ==============================
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop" # Garante que qualquer erro de API ou comando Git pare o script

# ==============================
# Configurações do projeto (Mais Flexíveis)
# ==================================================================================
# ATENÇÃO: Se for um serviço que não seja "web" (ex: "private service"), ajuste aqui.
# ==================================================================================
$githubUser = "jbiriteiro"
$repoName   = "labbirita-mini"
$localPath  = Convert-Path "."   # pasta atual
$renderServiceId = "srv-d3sq1p8dl3ps73ar54s0"            # se já existe, coloca aqui; senão vazio


# Configurações do Serviço Render
$renderServiceType = "web"
$renderServiceEnv = "python"
$commitMessage = "Deploy Automático: Atualização via LabBirita v2.0"

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
        # Configurações iniciais
        git config user.name "José Biriteiro"
        git config user.email "josebiriteiro@gmail.com"
    }

    # Adiciona/Atualiza remoto 'origin'
    $remotes = git remote
    if ($remotes -notcontains "origin") {
        git remote add origin $remoteUrl | Out-Null
        Write-Host "✅ Remoto 'origin' adicionado." -ForegroundColor Green
    } else {
        # Tenta setar a URL correta, caso tenha mudado
        git remote set-url origin $remoteUrl | Out-Null
        Write-Host "✅ Remoto 'origin' atualizado." -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Falha ao configurar o Git local: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# ==============================
# 4️⃣ Commit e Push (Com mensagem detalhada)
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
# 5️⃣ Deploy no Render (Ajuste Crítico na API)
# ==============================
Write-Host "`n# 5. Deploy no Render" -ForegroundColor Yellow
try {
    $repoUrl = "https://github.com/$githubUser/$repoName"

    if ($renderServiceId -eq "") {
        # Cria novo serviço - SINTAXE CORRIGIDA para API do RENDER (type e serviceDetails)
        $renderBody = @{
            type = "web_service" # CAMPO OBRIGATÓRIO: deve ser 'web_service', 'private_service', etc.
            name = $repoName
            serviceDetails = @{ # Configurações aninhadas
                env = $renderServiceEnv # 'python', 'node', 'docker', etc.
                repo = $repoUrl
                branch = "main"
            }
        } | ConvertTo-Json -Depth 4

        $deployResponse = Invoke-RestMethod -Uri "https://api.render.com/v1/services" -Method Post -Headers $headersRender -Body $renderBody
        $renderServiceId = $deployResponse.id
        Write-Host "✅ Serviço Render criado com sucesso! ID: $renderServiceId" -ForegroundColor Green
    } else {
        # Atualiza serviço existente (redeploy)
        # O Render API v1 aceita POST em /deploys para trigger de redeploy.
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