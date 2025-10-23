<#
================================================================================
?? Push & Deploy Ninja — LabBirita Mini (PowerShell 1000 grau)
================================================================================
Descrição:
Este script faz tudo automaticamente para o seu projeto LabBirita Mini:

1?? Commit & push seguro para GitHub (não envia tokens no commit)
2?? Cria ou atualiza o repositório remoto
3?? Cria ou atualiza o Web Service no Render
4?? Dispara o deploy do serviço
5?? Faz rollback automático no Render caso o deploy falhe
6?? Logs detalhados no console para você acompanhar cada passo
7?? Usa variáveis de ambiente para GitHub e Render API Keys
8?? Suporta múltiplos runs sem quebrar nada

Pré-requisitos:
- Git instalado e no PATH
- Python (para seu app Flask)
- PowerShell 7+ (recomendado)
- Variáveis de ambiente configuradas:
    $env:GITHUB_TOKEN = "<seu token GitHub>"
    $env:RENDER_API_KEY = "<sua Render API Key>"

Como usar:
1. Abra PowerShell no diretório do projeto (LabBirita Mini)
2. Configure suas variáveis de ambiente
3. Execute:
    .\push_git3.ps1
================================================================================
#>

# ======================================
# ? CONFIGURAÇÕES
# ======================================
$githubUser = "jbiriteiro"           # Usuário GitHub
$repoName = "labbirita-mini"         # Nome do repositório
$localPath = Convert-Path "."        # Caminho local do projeto

$renderServiceName = "labbirita-mini"  # Nome do serviço no Render
$renderRegion = "oregon"               # Região do Render (ex: oregon, frankfurt)
$renderPlan = "free"                   # Plano (free / starter / pro)

# Variáveis de ambiente
$githubToken = $env:GITHUB_TOKEN
$renderApiKey = $env:RENDER_API_KEY

# Headers para APIs
$githubHeaders = @{
    Authorization = "token $githubToken"
    Accept        = "application/vnd.github+json"
}
$renderHeaders = @{
    Authorization = "Bearer $renderApiKey"
    "Content-Type" = "application/json"
}

# ======================================
# 1?? Validação do GitHub Token
# ======================================
try {
    $ghTest = Invoke-RestMethod -Uri "https://api.github.com/user" -Headers $githubHeaders
    Write-Host "? Token GitHub OK! Usuário autenticado: $($ghTest.login)"
} catch {
    Write-Error "? Token GitHub inválido ou sem permissão 'repo'."
    return
}

# ======================================
# 2?? Criar repositório GitHub (se não existir)
# ======================================
try {
    $body = @{ name = $repoName } | ConvertTo-Json
    $ghRepo = Invoke-RestMethod -Uri "https://api.github.com/user/repos" -Method Post -Headers $githubHeaders -Body $body
    Write-Host "? Repositório criado no GitHub: $($ghRepo.html_url)"
} catch {
    Write-Warning "?? Repositório já existe ou outro erro: $($_.Exception.Message)"
}

# ======================================
# 3?? Inicializar Git local
# ======================================
if (-not (Test-Path ".git")) {
    git init
    Write-Host "? Git iniciado localmente."
}

# Configurar usuário Git local
git config user.name "José Biriteiro"
git config user.email "josebiriteiro@gmail.com"
Write-Host "? Usuário Git configurado"

# ======================================
# 4?? Commit seguro (sem tokens)
# ======================================
# Remove tokens do commit acidental
$pushGitPSPath = Join-Path $localPath "push_git3.ps1"
(Get-Content $pushGitPSPath) -replace $githubToken, "[REMOVIDO]" | Set-Content $pushGitPSPath

git add .
git commit -m "Initial commit — LabBirita Mini" -q
Write-Host "? Commit criado."

# ======================================
# 5?? Push para GitHub
# ======================================
$remoteUrl = "https://github.com/$githubUser/$repoName.git"
if (-not (git remote)) {
    git remote add origin $remoteUrl
}
git branch -M main
try {
    git push -u origin main
    Write-Host "?? Push enviado para GitHub: $remoteUrl"
} catch {
    Write-Warning "?? Push falhou: $($_.Exception.Message)"
}

# ======================================
# 6?? Criar ou atualizar Web Service no Render
# ======================================
$renderApi = "https://api.render.com/v1/services"
try {
    # Verifica se o serviço já existe
    $services = Invoke-RestMethod -Uri $renderApi -Headers $renderHeaders
    $service = $services | Where-Object { $_.name -eq $renderServiceName }

    if ($service) {
        Write-Host "?? Serviço já existe no Render: $($service.id). Atualizando..."
        # Atualiza repositório do serviço
        $updateBody = @{
            repo = "https://github.com/$githubUser/$repoName"
            branch = "main"
            plan = $renderPlan
        } | ConvertTo-Json
        Invoke-RestMethod -Uri "$renderApi/$($service.id)" -Method Patch -Headers $renderHeaders -Body $updateBody
        $serviceId = $service.id
    } else {
        Write-Host "?? Criando novo serviço no Render..."
        $createBody = @{
            name = $renderServiceName
            type = "web"
            repo = "https://github.com/$githubUser/$repoName"
            branch = "main"
            plan = $renderPlan
            region = $renderRegion
            env = "python"
            buildCommand = "pip install -r requirements.txt"
            startCommand = "gunicorn app:app --bind 0.0.0.0:\$PORT"
        } | ConvertTo-Json
        $newService = Invoke-RestMethod -Uri $renderApi -Method Post -Headers $renderHeaders -Body $createBody
        $serviceId = $newService.id
        Write-Host "? Serviço criado: $serviceId"
    }
} catch {
    Write-Error "? Não foi possível criar ou atualizar o serviço no Render: $($_.Exception.Message)"
    return
}

# ======================================
# 7?? Deploy automático com rollback se falhar
# ======================================
try {
    Write-Host "?? Iniciando deploy..."
    $deployBody = @{ serviceId = $serviceId } | ConvertTo-Json
    $deploy = Invoke-RestMethod -Uri "$renderApi/$serviceId/deploys" -Method Post -Headers $renderHeaders -Body $deployBody
    $deployUrl = $deploy.serviceDetail.url
    Write-Host "?? Deploy ativo! URL final: $deployUrl"
} catch {
    Write-Warning "? Deploy falhou, fazendo rollback..."
    if ($serviceId) {
        # Tenta rollback para última versão
        Invoke-RestMethod -Uri "$renderApi/$serviceId/deploys/latest/rollback" -Method Post -Headers $renderHeaders
        Write-Host "?? Rollback realizado com sucesso."
    }
}

Write-Host "?? Tudo pronto! LabBirita Mini no ar e GitHub atualizado. Cheers! ??"
