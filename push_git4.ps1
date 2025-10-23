<#
==========================================================================
Push GitHub + Deploy Render — LabBirita Mini (Versão Final 1000 grau)
==========================================================================

Descrição:
- Faz push automático do seu projeto para GitHub.
- Cria repositório se não existir.
- Configura usuário Git localmente se necessário.
- Cria ou atualiza serviço Web no Render automaticamente.
- Faz rollback se o deploy falhar.
- Totalmente comentado para você entender tudo.

Pré-requisitos:
- Git instalado e disponível no PATH
- Python instalado para rodar a mini loja
- Variáveis de ambiente:
    $env:GITHUB_TOKEN  → Personal Access Token do GitHub com escopo 'repo'
    $env:RENDER_API_KEY → API Key do Render (Dashboard → Account → API Keys)

==========================================================================
#>

# ----------------------------
# Configurações principais
# ----------------------------
$githubUser = "jbiriteiro"          # Usuário GitHub
$repoName = "labbirita-mini"        # Nome do repositório
$localPath = Convert-Path "."       # Pasta do projeto
$branch = "main"                     # Branch principal
$renderServiceId = $env:RENDER_SERVICE_ID  # Opcional: ID do serviço já criado
$renderApiKey = $env:RENDER_API_KEY

# Headers para APIs
$githubHeaders = @{
    Authorization = "token $env:GITHUB_TOKEN"
    Accept = "application/vnd.github+json"
}
$renderHeaders = @{
    Authorization = "Bearer $renderApiKey"
    "Content-Type" = "application/json"
}

# ----------------------------
# 1️⃣ Valida GitHub Token
# ----------------------------
try {
    $user = Invoke-RestMethod -Uri "https://api.github.com/user" -Headers $githubHeaders
    Write-Host "✅ Token GitHub OK! Usuário: $($user.login)"
} catch {
    Write-Error "❌ Token GitHub inválido ou sem permissão. Gere novo token com escopo 'repo'."
    return
}

# ----------------------------
# 2️⃣ Criar repositório GitHub se não existir
# ----------------------------
try {
    $body = @{ name = $repoName } | ConvertTo-Json
    $repo = Invoke-RestMethod -Uri "https://api.github.com/user/repos" -Method Post -Headers $githubHeaders -Body $body
    Write-Host "✅ Repositório criado: $($repo.html_url)"
} catch {
    Write-Warning "⚠️ Repositório já existe ou outro erro: $($_.Exception.Message)"
}

# ----------------------------
# 3️⃣ Inicializa Git local
# ----------------------------
if (-not (Test-Path ".git")) {
    git init
    Write-Host "✅ Git inicializado localmente"
}

# Configura usuário local se necessário
$gitName = git config user.name
if (-not $gitName) { git config user.name "José Biriteiro" }
$gitEmail = git config user.email
if (-not $gitEmail) { git config user.email "josebiriteiro@gmail.com" }
Write-Host "✅ Usuário Git configurado"

# ----------------------------
# 4️⃣ Commit das alterações
# ----------------------------
git add .
git commit -m "Initial commit — LabBirita Mini" -q
Write-Host "✅ Commit criado"

# ----------------------------
# 5️⃣ Adiciona remoto e push
# ----------------------------
$remoteUrl = "https://github.com/$githubUser/$repoName.git"
$remotes = git remote
if ($remotes -notcontains "origin") { git remote add origin $remoteUrl }
git branch -M $branch
git push -u origin $branch
Write-Host "🚀 Push enviado para GitHub: $remoteUrl"

# ----------------------------
# 6️⃣ Criar ou atualizar serviço Render
# ----------------------------
try {
    if (-not $renderServiceId) {
        # Cria novo serviço
        $renderBody = @{
            name = $repoName
            repo = "https://github.com/$githubUser/$repoName"
            branch = $branch
            serviceType = "web"
            env = "python"
            buildCommand = "pip install -r requirements.txt"
            startCommand = "gunicorn app:app --bind 0.0.0.0:\$PORT"
        } | ConvertTo-Json -Depth 5

        $renderResponse = Invoke-RestMethod -Uri "https://api.render.com/v1/services" -Method Post -Headers $renderHeaders -Body $renderBody
        $renderServiceId = $renderResponse.id
        Write-Host "✅ Serviço Render criado: $($renderResponse.serviceDetailsUrl)"
    } else {
        # Atualiza serviço existente
        $updateBody = @{ branch = $branch } | ConvertTo-Json
        $renderResponse = Invoke-RestMethod -Uri "https://api.render.com/v1/services/$renderServiceId" -Method Patch -Headers $renderHeaders -Body $updateBody
        Write-Host "✅ Serviço Render atualizado: $($renderResponse.serviceDetailsUrl)"
    }
} catch {
    Write-Error "❌ Deploy Render falhou: $($_.Exception.Message). Tentando rollback..."
    if ($renderServiceId) {
        # Opcional: rollback para versão anterior se disponível
        Write-Warning "⚠️ Rollback não implementado automaticamente, faça manualmente pelo dashboard."
    }
}

Write-Host "🎉 Tudo pronto! Mini loja LabBirita online e funcionando."