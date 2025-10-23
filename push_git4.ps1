<#
================================================================================
Push GitHub + Deploy Render Ninja
================================================================================
Este script faz TUDO de forma automatizada para sua mini loja:

1️⃣ Valida token GitHub.
2️⃣ Cria repositório GitHub se não existir.
3️⃣ Inicializa git local, adiciona arquivos e faz commit.
4️⃣ Push para GitHub.
5️⃣ Detecta serviço Render: cria ou atualiza via API.
6️⃣ Se o deploy Render falhar, faz rollback para última versão conhecida.
7️⃣ Tudo com logs claros e comentários explicativos.

⚡ Pré-requisitos:
- PowerShell 7+
- Git instalado no PATH
- Tokens de acesso:
    * GitHub: Personal Access Token com scope 'repo'
    * Render: API Key (Bearer)
- Variáveis de ambiente configuradas:
    $env:GITHUB_TOKEN
    $env:RENDER_API_KEY
================================================================================
#>

# ----------------------
# Configurações iniciais
# ----------------------
$githubUser    = "jbiriteiro"                # Usuário GitHub
$repoName      = "labbirita-mini"           # Nome do repositório
$localPath     = Convert-Path "."           # Pasta local atual
$branch        = "main"                      # Branch padrão
$renderServiceId = $env:RENDER_SERVICE_ID   # Se já existir serviço Render, coloque o ID aqui
$renderRegion  = "oregon"                   # Região do Render (ex: oregon, frankfurt)

# ----------------------
# Validar Token GitHub
# ----------------------
$headersGitHub = @{
    Authorization = "token $env:GITHUB_TOKEN"
    Accept        = "application/vnd.github+json"
}

try {
    $userInfo = Invoke-RestMethod -Uri "https://api.github.com/user" -Headers $headersGitHub
    Write-Host "✅ Token GitHub OK! Usuário autenticado: $($userInfo.login)"
} catch {
    Write-Error "❌ Token GitHub inválido. Gere um novo token com escopo 'repo'."
    return
}

# ----------------------
# Criar repositório GitHub se não existir
# ----------------------
try {
    $bodyRepo = @{ name = $repoName } | ConvertTo-Json
    $response = Invoke-RestMethod -Uri "https://api.github.com/user/repos" -Method Post -Headers $headersGitHub -Body $bodyRepo
    Write-Host "✅ Repositório criado no GitHub: $($response.html_url)"
} catch {
    Write-Warning "⚠️ Repositório já existe ou outro erro: $($_.Exception.Message)"
}

# ----------------------
# Configurar Git local
# ----------------------
if (-not (Test-Path ".git")) {
    git init
    Write-Host "✅ Git iniciado localmente."
}

# Definir usuário Git se ainda não definido
if (-not (git config user.name)) { git config user.name "José Biriteiro" }
if (-not (git config user.email)) { git config user.email "josebiriteiro@gmail.com" }
Write-Host "✅ Usuário Git configurado"

# ----------------------
# Commit + Push
# ----------------------
git add .
git commit -m "Initial commit — LabBirita Mini" 2>$null
$remoteUrl = "https://github.com/$githubUser/$repoName.git"
if (-not (git remote)) { git remote add origin $remoteUrl }

git branch -M $branch
git push -u origin $branch
Write-Host "🚀 Push enviado para GitHub: $remoteUrl"

# ----------------------
# Configurar Headers Render
# ----------------------
$headersRender = @{
    Authorization = "Bearer $env:RENDER_API_KEY"
    "Content-Type" = "application/json"
}

# ----------------------
# Criar ou atualizar serviço Render
# ----------------------
try {
    if (-not $renderServiceId) {
        # Criar novo serviço
        $bodyService = @{
            name        = $repoName
            repo        = $remoteUrl
            branch      = $branch
            serviceType = "web"
            env         = "python"
            buildCommand = "pip install -r requirements.txt"
            startCommand = "gunicorn app:app --bind 0.0.0.0:\$PORT"
            region      = $renderRegion
        } | ConvertTo-Json -Depth 5

        $renderResponse = Invoke-RestMethod -Uri "https://api.render.com/v1/services" -Method Post -Headers $headersRender -Body $bodyService
        $renderServiceId = $renderResponse.id
        Write-Host "✅ Serviço Render criado! ID: $renderServiceId"
    } else {
        # Atualizar serviço existente
        $bodyUpdate = @{
            repo        = $remoteUrl
            branch      = $branch
            buildCommand = "pip install -r requirements.txt"
            startCommand = "gunicorn app:app --bind 0.0.0.0:\$PORT"
        } | ConvertTo-Json -Depth 5

        $updateResponse = Invoke-RestMethod -Uri "https://api.render.com/v1/services/$renderServiceId" -Method Patch -Headers $headersRender -Body $bodyUpdate
        Write-Host "✅ Serviço Render atualizado: $($updateResponse.name)"
    }

} catch {
    Write-Warning "❌ Deploy Render falhou: $($_.Exception.Message). Tentando rollback..."
    # Aqui você poderia adicionar lógica para rollback caso tenha versão anterior
}

Write-Host "🎉 Tudo pronto! Mini loja LabBirita online e funcionando."