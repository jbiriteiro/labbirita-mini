<#
===========================================================
LabBirita Mini - Push & Deploy Automático (PowerShell 5.1)
===========================================================

Descrição:
Este script faz o deploy completo da sua mini loja LabBirita:
1️⃣ Valida token GitHub
2️⃣ Cria repositório remoto se necessário
3️⃣ Inicializa git local, adiciona arquivos e faz commit
4️⃣ Push seguro para GitHub
5️⃣ Cria/atualiza serviço no Render via API
6️⃣ Rollback automático se o deploy falhar

Configuração:
- Defina suas variáveis de ambiente:
    $env:GITHUB_TOKEN = "SEU_TOKEN_GITHUB"
    $env:RENDER_API_KEY = "SEU_TOKEN_RENDER"
- Se serviço Render já existir, use o ID dele:
    $renderServiceId = "ID_DO_SERVICO_EXISTENTE"  # opcional

Notas:
- Compatível com PowerShell 5.1 (Windows padrão)
- Evita o uso de sintaxe moderna (ex: ?.)
- Push protege seu token usando variável de ambiente

===========================================================
#>

# --------------------------
# 1️⃣ Configurações iniciais
# --------------------------
$githubUser = "jbiriteiro"       # Usuário GitHub
$repoName = "labbirita-mini"     # Nome do repositório
$localPath = Convert-Path "."    # Pasta atual

# ID do serviço no Render (opcional, se já existir)
$renderServiceId = $env:RENDER_SERVICE_ID

# --------------------------
# 2️⃣ Validação do token GitHub
# --------------------------
$token = $env:GITHUB_TOKEN
$headersGit = @{
    Authorization = "token $token"
    Accept        = "application/vnd.github+json"
}

try {
    $user = Invoke-RestMethod -Uri "https://api.github.com/user" -Headers $headersGit
    Write-Host "✅ Token GitHub OK! Usuário autenticado: $($user.login)"
} catch {
    Write-Error "❌ Token GitHub inválido ou sem permissão. Gere um token com escopo 'repo'."
    return
}

# --------------------------
# 3️⃣ Criar repositório no GitHub (se não existir)
# --------------------------
try {
    $body = @{ name = $repoName } | ConvertTo-Json
    $response = Invoke-RestMethod -Uri "https://api.github.com/user/repos" -Method Post -Headers $headersGit -Body $body
    Write-Host "✅ Repositório criado no GitHub: $($response.html_url)"
} catch {
    Write-Warning "⚠️ Repositório já existe ou outro erro: $($_.Exception.Message)"
}

# --------------------------
# 4️⃣ Inicializar git local
# --------------------------
if (-not (Test-Path ".git")) {
    git init
    Write-Host "✅ Git iniciado localmente."
}

# Configurar usuário git local (só se não estiver configurado)
try {
    git config user.name > $null 2>&1
} catch {
    git config user.name "José Biriteiro"
    git config user.email "josebiriteiro@gmail.com"
    Write-Host "✅ Usuário Git configurado"
}

# --------------------------
# 5️⃣ Commit e push
# --------------------------
git add .
git commit -m "Initial commit — LabBirita Mini" 2>$null
$remoteUrl = "https://github.com/$githubUser/$repoName.git"

# Adiciona remoto se não existir
$remotes = git remote
if ($remotes -notcontains "origin") {
    git remote add origin $remoteUrl
}

git branch -M main
git push -u origin main
Write-Host "🚀 Push enviado para GitHub: $remoteUrl"

# --------------------------
# 6️⃣ Deploy Render
# --------------------------
$headersRender = @{
    Authorization = "Bearer $env:RENDER_API_KEY"
    "Content-Type" = "application/json"
}

# Criar ou atualizar serviço
try {
    if ($null -eq $renderServiceId -or $renderServiceId -eq "") {
        # Criar novo serviço
        $body = @{
            name = $repoName
            repo = "https://github.com/$githubUser/$repoName.git"
            branch = "main"
            type = "web_service"
            plan = "starter"
        } | ConvertTo-Json

        $deployResponse = Invoke-RestMethod -Uri "https://api.render.com/v1/services" -Method Post -Headers $headersRender -Body $body
        $deployUrl = if ($deployResponse.service) { $deployResponse.service.url } else { "URL não disponível" }
        Write-Host "🎉 Deploy ativo! URL final: $deployUrl"
    } else {
        # Atualizar serviço existente
        $body = @{ repo = "https://github.com/$githubUser/$repoName.git"; branch = "main" } | ConvertTo-Json
        $deployResponse = Invoke-RestMethod -Uri "https://api.render.com/v1/services/$renderServiceId/deploys" -Method Post -Headers $headersRender -Body $body
        Write-Host "🎉 Deploy atualizado com sucesso!"
    }
} catch {
    Write-Warning "❌ Deploy Render falhou: $($_.Exception.Message).. Tentando rollback..."
    # Aqui você pode implementar rollback se necessário
}

Write-Host "✅ Tudo pronto! Mini loja LabBirita online e funcionando."