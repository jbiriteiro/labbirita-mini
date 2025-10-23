# =====================================================
# Push GitHub automático seguro
# =====================================================

# ⚡ Configurações iniciais
$githubUser = "jbiriteiro"        # Seu usuário do GitHub
$repoName   = "labbirita-mini"    # Nome do repositório a criar

# Pega token da variável de ambiente
$token = $env:GITHUB_TOKEN
if (-not $token) {
    Write-Error "❌ Nenhum token encontrado! Defina a variável de ambiente GITHUB_TOKEN."
    return
}

# Pasta local
$localPath = Convert-Path "."

# Headers para API
$headers = @{
    Authorization = "token $token"
    Accept = "application/vnd.github+json"
}

# =========================
# 1️⃣ Validação do token
# =========================
try {
    $test = Invoke-RestMethod -Uri "https://api.github.com/user" -Headers $headers
    Write-Host "✅ Token OK! Usuário autenticado: $($test.login)"
} catch {
    Write-Error "❌ Token inválido ou sem permissão. Gere um novo token com escopo 'repo'."
    return
}

# =========================
# 2️⃣ Criar repositório no GitHub (se não existir)
# =========================
try {
    $body = @{ name = $repoName } | ConvertTo-Json
    $response = Invoke-RestMethod -Uri "https://api.github.com/user/repos" -Method Post -Headers $headers -Body $body
    Write-Host "✅ Repositório criado no GitHub: $($response.html_url)"
} catch {
    Write-Warning "⚠️ Repositório já existe ou outro erro: $($_.Exception.Message)"
}

# =========================
# 3️⃣ Configurar git local
# =========================
if (-not (Test-Path ".git")) {
    git init
    Write-Host "✅ Git iniciado localmente."
}

# Configura usuário Git se não estiver definido
$userName  = git config user.name
$userEmail = git config user.email
if (-not $userName -or -not $userEmail) {
    git config user.name "José Biriteiro"
    git config user.email "josebiriteiro@gmail.com"
    Write-Host "✅ Usuário Git configurado: José Biriteiro <josebiriteiro@gmail.com>"
}

# =========================
# 4️⃣ Adicionar arquivos e commit
# =========================
git add .
git commit -m "Initial commit — LabBirita Mini" -q
Write-Host "✅ Commit criado."

# =========================
# 5️⃣ Adicionar remoto e push
# =========================
$remoteUrl = "https://$githubUser@github.com/$githubUser/$repoName.git"

# Adiciona remoto se ainda não
$remotes = git remote
if ($remotes -notcontains "origin") {
    git remote add origin $remoteUrl
}

# Push para main (ou master)
git branch -M main
git push -u origin main
Write-Host "🚀 Push seguro enviado para GitHub: https://github.com/$githubUser/$repoName"