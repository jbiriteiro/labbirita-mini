<#
================================================================================
LabBirita Mini - Deploy Automático 1000 grau (v4.1 - Corrigido e Seguro)
--------------------------------------------------------------------------------
Data: 24/10/2025
Autor: José Biriteiro
Descrição:
Este script automatiza o deploy da mini loja LabBirita com segurança e robustez:
1️⃣ Carrega .env
2️⃣ Valida tokens
3️⃣ Testa autenticação no GitHub (com retry)
4️⃣ Verifica/cria repositório remoto
5️⃣ Configura Git local com credencial segura (sem token na URL!)
6️⃣ Commit + Push
7️⃣ Redeploy no Render (com retry)
8️⃣ Feedback colorido e claro
================================================================================
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ==============================
# Configurações do Projeto
# ==============================
$githubUser      = "jbiriteiro"
$repoName        = "labbirita-mini"
$localPath       = Convert-Path "."
$renderServiceId = "srv-d3sq1p8dl3ps73ar54s0"
$commitMessage   = "Deploy Automático: Correção final v4.1 (seguro + retry)"

# ==============================
# Funções de Utilidade
# ==============================

function Load-EnvFile {
    $envFilePath = Join-Path $localPath ".env"
    if (Test-Path $envFilePath) {
        Write-Host "✅ Arquivo .env encontrado. Carregando variáveis..." -ForegroundColor DarkGreen
        Get-Content $envFilePath | ForEach-Object {
            if ($_ -match "^\s*#") { return }
            elseif ($_ -match "^\s*([a-zA-Z_]+)\s*=\s*['""]?(.*?)['""]?\s*$") {
                Set-Item "env:\$($Matches[1])" $Matches[2].Trim()
                Write-Host "   -> $($Matches[1]) carregado." -ForegroundColor DarkGray
            }
        }
    } else {
        Write-Host "⚠️ Arquivo .env não encontrado." -ForegroundColor Yellow
    }
}

function Validate-Env {
    if (-not $env:GITHUB_TOKEN) { Write-Host "❌ GITHUB_TOKEN não encontrado" -ForegroundColor Red; exit 1 }
    if (-not $env:RENDER_API_KEY) { Write-Host "❌ RENDER_API_KEY não encontrado" -ForegroundColor Red; exit 1 }
}

function Invoke-RestMethodWithRetry {
    param(
        [string]$Uri,
        [hashtable]$Headers,
        [string]$Method = "GET",
        [object]$Body = $null,
        [int]$MaxRetries = 3
    )
    $retry = 0
    while ($retry -lt $MaxRetries) {
        try {
            $params = @{
                Uri     = $Uri.Trim()
                Headers = $Headers
                Method  = $Method
            }
            if ($Body) { $params.Body = $Body }
            return Invoke-RestMethod @params
        } catch {
            $retry++
            if ($retry -ge $MaxRetries) { throw $_ }
            Write-Host "⚠️ Tentativa $retry falhou. Aguardando 2s..." -ForegroundColor Yellow
            Start-Sleep -Seconds 2
        }
    }
}

function Test-GitHubAuth {
    try {
        $user = Invoke-RestMethodWithRetry -Uri "https://api.github.com/user" -Headers $script:headersGitHub
        Write-Host "✅ Token GitHub OK! Usuário: $($user.login)" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "❌ Token inválido ou sem permissão. Verifique o .env e o escopo 'repo'." -ForegroundColor Red
        return $false
    }
}

function Test-GitHubRemote {
    $repoApiUrl = "https://api.github.com/repos/$githubUser/$repoName"
    try {
        $repo = Invoke-RestMethodWithRetry -Uri $repoApiUrl -Headers $script:headersGitHub
        Write-Host "✅ Repositório remoto existe: $($repo.html_url)" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "⚠️ Repositório remoto não encontrado ou inacessível" -ForegroundColor Yellow
        return $false
    }
}

function Create-GitHubRepo {
    try {
        $body = @{ name = $repoName; private = $true } | ConvertTo-Json
        $response = Invoke-RestMethodWithRetry -Uri "https://api.github.com/user/repos" -Method Post -Headers $script:headersGitHub -Body $body
        Write-Host "✅ Repositório criado no GitHub: $($response.html_url)" -ForegroundColor Green
    } catch {
        Write-Host "ℹ️ Possível repositório já existente ou erro não crítico." -ForegroundColor DarkYellow
    }
}

function Init-LocalGit {
    $remoteUrl = "https://github.com/$githubUser/$repoName.git"
    try {
        if (-not (Test-Path ".git")) {
            git init | Out-Null
            git config user.name "José Biriteiro"
            git config user.email "josebiriteiro@gmail.com"
            Write-Host "✅ Git iniciado localmente" -ForegroundColor Green
        }

        $remotes = git remote
        if ($remotes -notcontains "origin") {
            git remote add origin $remoteUrl | Out-Null
        } else {
            git remote set-url origin $remoteUrl | Out-Null
        }

        # Configura credencial temporária SEM expor token na URL
        git config --local credential.helper "!f() { echo username=$githubUser; echo password=`$env:GITHUB_TOKEN; };f" | Out-Null
        Write-Host "✅ Git configurado com credencial segura (token não visível na URL)" -ForegroundColor Green
    } catch {
        Write-Host "❌ Falha ao configurar Git local: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
}

function Commit-And-Push {
    try {
        git add . | Out-Null
        $status = git status --porcelain
        if (-not $status) {
            Write-Host "ℹ️ Nenhuma alteração detectada. Nenhum commit será feito." -ForegroundColor Cyan
            return
        }
        git commit -m "$commitMessage" | Out-Null
        git branch -M main | Out-Null
        git push -u origin main | Out-Null
        Write-Host "🚀 Push enviado para GitHub: https://github.com/$githubUser/$repoName" -ForegroundColor Cyan
    } catch {
        Write-Host "❌ Falha no Commit/Push: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
}

function Redeploy-Render {
    try {
        $deployUrl = "https://api.render.com/v1/services/$renderServiceId/deploys"
        Invoke-RestMethodWithRetry -Uri $deployUrl -Method Post -Headers $script:headersRender | Out-Null
        Write-Host "✅ Redeploy solicitado com sucesso: $renderServiceId" -ForegroundColor Green

        $serviceUrl = "https://api.render.com/v1/services/$renderServiceId"
        $serviceDetails = Invoke-RestMethodWithRetry -Uri $serviceUrl -Headers $script:headersRender
        if ($serviceDetails.serviceDetails.url) {
            Write-Host "🌐 URL do Serviço: $($serviceDetails.serviceDetails.url)" -ForegroundColor Cyan
        }
    } catch {
        Write-Host "❌ Deploy Render falhou. Verifique a chave API e o ID do serviço." -ForegroundColor Red
        Write-Host "♻️ (Rollback manual recomendado — este script não força revert automático por segurança)" -ForegroundColor Yellow
        exit 1
    }
}

# ==============================
# Execução Principal
# ==============================
Write-Host "`n🎯 Iniciando Deploy Automático LabBirita Mini (v4.1)..." -ForegroundColor Magenta

Load-EnvFile
Validate-Env

$script:headersGitHub = @{
    Authorization = "token $env:GITHUB_TOKEN"
    Accept        = "application/vnd.github+json"
}
$script:headersRender = @{
    Authorization = "Bearer $env:RENDER_API_KEY"
    "Content-Type" = "application/json"
}

if (-not (Test-GitHubAuth)) { exit 1 }
if (-not (Test-GitHubRemote)) { Create-GitHubRepo }
Init-LocalGit
Commit-And-Push
Redeploy-Render

Write-Host "`n🎉 DEPLOY CONCLUÍDO COM SUCESSO!" -ForegroundColor Magenta
Write-Host "------------------------------------------------------" -ForegroundColor Magenta
Write-Host "⚠️ Confira o log do Render para garantir que o build foi bem-sucedido." -ForegroundColor Yellow