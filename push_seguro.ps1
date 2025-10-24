<#
================================================================================
LabBirita Mini - Push Seguro Automático
Autor: José Biriteiro
Data: 23/10/2025
Descrição:
- Remove .env do histórico e do stage
- Adiciona .env ao .gitignore
- Reescreve histórico para remover qualquer commit antigo do .env
- Commit limpo e push forçado para origin/main
- Pronto para ser usado antes de qualquer deploy
================================================================================
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Caminho do projeto
$localPath = Convert-Path "."

# Arquivo secreto
$secretFile = ".env"

Write-Host "`n🎯 Iniciando Push Seguro LabBirita Mini..." -ForegroundColor Magenta

# 1️⃣ Remove .env do Git (cache) e adiciona ao .gitignore
if (Test-Path $secretFile) {
    Write-Host "✅ Removendo $secretFile do controle do Git..." -ForegroundColor Green
    git rm --cached $secretFile
    Write-Host "✅ Adicionando $secretFile ao .gitignore..." -ForegroundColor Green
    if (-not (Select-String -Path ".gitignore" -Pattern "$secretFile" -Quiet)) {
        Add-Content .gitignore $secretFile
    }
    git add .gitignore
    git commit -m "Remove .env do Git e adiciona ao .gitignore" | Out-Null
}

# 2️⃣ Reescreve histórico para remover qualquer commit antigo do .env
Write-Host "⚡ Reescrevendo histórico para remover .env de commits antigos..." -ForegroundColor Yellow
git filter-branch --force --index-filter "git rm --cached --ignore-unmatch $secretFile" --prune-empty --tag-name-filter cat -- --all

# 3️⃣ Commit limpo (sem arquivos secretos)
Write-Host "✅ Commit limpo pronto..." -ForegroundColor Green

# 4️⃣ Força push pro GitHub
Write-Host "🚀 Enviando push forçado para origin/main..." -ForegroundColor Cyan
git push origin main --force

Write-Host "`n🎉 Push Seguro Concluído! Seu repositório está limpo e pronto para deploy." -ForegroundColor Magenta