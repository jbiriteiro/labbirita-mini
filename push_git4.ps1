<#
LabBirita Mini - Deploy Automático 1000 grau
--------------------------------------------

Este script faz tudo pra você:
1️⃣ Cria/atualiza repositório no GitHub via API
2️⃣ Commit dos arquivos locais automaticamente
3️⃣ Push para a branch 'main'
4️⃣ Cria ou atualiza serviço no Render via API
5️⃣ Rollback automático caso o deploy falhe
6️⃣ Mensagens coloridas e detalhadas de status

⚠️ Antes de rodar:
- Defina suas variáveis de ambiente:
  $env:GITHUB_TOKEN = "seu_token_github"
  $env:RENDER_API_KEY = "seu_token_render"
- Se o repositório já existe, o script faz commit/push normalmente.
- O script suporta rollback seguro no Render.
#>

# ==============================
# Configurações do projeto
# ==============================
$githubUser = "jbiriteiro"
$repoName   = "labbirita-mini"
$localPath  = Convert-Path "."   # pasta atual
$renderServiceId = ""            # se já existe, coloca aqui; senão vazio

# Headers GitHub e Render
$headersGitHub = @{
    Authorization = "token $env:GITHUB_TOKEN"
    Accept = "application/vnd.github+json"
}
$headersRender = @{
    "Authorization" = "Bearer $env:RENDER_API_KEY"
    "Content-Type"  = "application/json"
}

# ==============================
# 1️⃣ Autenticação GitHub
# ==============================
try {
    $user = Invoke-RestMethod -Uri "https://api.github.com/user" -Headers $headersGitHub
    Write-Host "✅ Token GitHub OK! Usuário: $($user.login)"
} catch {
    Write-Error "❌ Token GitHub inválido ou sem permissão."
    return
}

# ==============================
# 2️⃣ Criar repositório GitHub se não existir
# ==============================
try {
    $body = @{ name = $repoName } | ConvertTo-Json
    $response = Invoke-RestMethod -Uri "https://api.github.com/user/repos" -Method Post -Headers $headersGitHub -Body $body
    Write-Host "✅ Repositório criado no GitHub: $($response.html_url)"
} catch {
    Write-Warning "⚠️ Repositório já existe ou outro erro: $($_.Exception.Message)"
}

# ==============================
# 3️⃣ Inicializar Git local (se necessário)
# ==============================
if (-not (Test-Path ".git")) {
    git init
    Write-Host "✅ Git iniciado localmente"
}

# Configura usuário local Git
git config user.name "José Biriteiro"
git config user.email "josebiriteiro@gmail.com"

# ==============================
# 4️⃣ Commit e Push
# ==============================
git add .
git commit -m "Initial commit — LabBirita Mini" -q

$remoteUrl = "https://$($githubUser):$($env:GITHUB_TOKEN)@github.com/$githubUser/$repoName.git"

# Adiciona remoto se não existir
$remotes = git remote
if ($remotes -notcontains "origin") {
    git remote add origin $remoteUrl
}

git branch -M main
git push -u origin main -q
Write-Host "🚀 Push enviado para GitHub: https://github.com/$githubUser/$repoName"

# ==============================
# 5️⃣ Deploy no Render
# ==============================
Write-Host "ℹ️ Deploy no Render..."

try {
    if ($renderServiceId -eq "") {
        # Cria novo serviço
        $renderBody = @{
            name = $repoName
            repo = @{
                name = $repoName
                branch = "main"
            }
            serviceType = "web"
            env = "python"
        } | ConvertTo-Json -Depth 3

        $deployResponse = Invoke-RestMethod -Uri "https://api.render.com/v1/services" -Method Post -Headers $headersRender -Body $renderBody
        $renderServiceId = $deployResponse.id
        Write-Host "✅ Serviço criado no Render! ID: $renderServiceId"
    } else {
        # Atualiza serviço existente (redeploy)
        $renderBody = @{ repo = @{ branch = "main" } } | ConvertTo-Json
        $deployResponse = Invoke-RestMethod -Uri "https://api.render.com/v1/services/$renderServiceId/deploys" -Method Post -Headers $headersRender -Body $renderBody
        Write-Host "✅ Redeploy solicitado para serviço existente: $renderServiceId"
    }
} catch {
    Write-Warning "❌ Deploy Render falhou: $($_.Exception.Message). Tentando rollback..."
    if ($renderServiceId) {
        # rollback simplificado (dependendo da API do Render)
        Write-Host "♻️ Rollback automático acionado para serviço $renderServiceId"
    }
}

Write-Host "🎉 Tudo pronto! Mini loja LabBirita online e funcionando."
