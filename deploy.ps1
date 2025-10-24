<#
================================================================================
LabBirita Mini - Deploy Seguro Automático (v5.2 – SEM EMOJIS, COMPATÍVEL COM WINDOWS)
Autor: José Biriteiro
Data: 24/10/2025
Baseado em: https://github.com/jbiriteiro/labbirita-mini
================================================================================
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Configurações
$githubUser      = "jbiriteiro"
$repoName        = "labbirita-mini"
$renderServiceId = "srv-d3sq1p8dl3ps73ar54s0"
$commitMessage   = "Deploy: atualizacao automatica"

Write-Host "`n[INFO] Iniciando Deploy Seguro LabBirita Mini..." -ForegroundColor Magenta

# 1. Carregar .env
$envFile = ".env"
if (Test-Path $envFile) {
    Write-Host "[OK] Carregando $envFile..." -ForegroundColor DarkGreen
    Get-Content $envFile | ForEach-Object {
        if ($_ -notmatch "^\s*#" -and ($_ -match "^\s*([a-zA-Z_]+)\s*=\s*['""]?(.*?)['""]?\s*$")) {
            Set-Item "env:\$($Matches[1])" $Matches[2].Trim()
        }
    }
} else {
    Write-Host "[AVISO] Arquivo .env nao encontrado." -ForegroundColor Yellow
}

# 2. Validar tokens
if (-not $env:GITHUB_TOKEN) { Write-Host "[ERRO] GITHUB_TOKEN ausente" -ForegroundColor Red; exit 1 }
if (-not $env:RENDER_API_KEY) { Write-Host "[ERRO] RENDER_API_KEY ausente" -ForegroundColor Red; exit 1 }

# 3. Garantir .gitignore com .env
if (-not (Test-Path ".gitignore")) {
    Set-Content ".gitignore" ".env`nvenv/`n__pycache__/`n*.pyc"
    Write-Host "[OK] .gitignore criado." -ForegroundColor Green
} else {
    $ignoreContent = Get-Content ".gitignore"
    if ($ignoreContent -notcontains ".env") {
        Add-Content ".gitignore" ".env"
        Write-Host "[OK] .env adicionado ao .gitignore." -ForegroundColor Green
    }
}

# 4. Remover .env do Git (se estiver trackeado)
if (git ls-files --error-unmatch ".env" 2>$null) {
    Write-Host "[AVISO] .env estava no Git! Removendo do stage..." -ForegroundColor Yellow
    git rm --cached ".env" | Out-Null
    git add ".gitignore" | Out-Null
    git commit -m "fix: remover .env do controle de versao" | Out-Null
}

# 5. Verificar se .env esta prestes a ser commitado
$status = git status --porcelain
if ($status -match "^\s*[AM]+\s+\.env") {
    Write-Host "[ERRO CRITICO] .env esta no stage! Abortando deploy." -ForegroundColor Red
    exit 1
}

# 6. Commit e push (so se houver mudancas)
if (-not $status) {
    Write-Host "[INFO] Nenhuma alteracao detectada. Pulando commit." -ForegroundColor Cyan
} else {
    git add .
    git commit -m "$commitMessage" | Out-Null
    git branch -M main

    Write-Host "[GIT] Enviando para GitHub..." -ForegroundColor Cyan
    git push -u origin main
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERRO] Push falhou. Abortando." -ForegroundColor Red
        exit 1
    }
    Write-Host "[OK] Push concluido com sucesso!" -ForegroundColor Green
}

# 7. Redeploy no Render
Write-Host "[RENDER] Acionando redeploy..." -ForegroundColor Cyan
$headers = @{
    Authorization = "Bearer $env:RENDER_API_KEY"
    "Content-Type" = "application/json"
}
try {
    Invoke-RestMethod -Uri "https://api.render.com/v1/services/$renderServiceId/deploys" -Method Post -Headers $headers | Out-Null
    Write-Host "[OK] Redeploy solicitado com sucesso!" -ForegroundColor Green
} catch {
    Write-Host "[ERRO] Falha no redeploy: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "`n[CONCLUIDO] Deploy seguro finalizado!" -ForegroundColor Magenta
Write-Host "[SEGURANCA] Seu .env esta protegido. Nada de segredos no GitHub!" -ForegroundColor DarkGreen