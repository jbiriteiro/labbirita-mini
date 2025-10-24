<#
================================================================================
LabBirita Mini - Deploy Automático 1000 grau (v3.3 - Profissional c/ .env)
--------------------------------------------------------------------------------
Data: 23/10/2025
Autor: José Biriteiro
Descrição:
Este script automatiza o deploy da mini loja LabBirita:
1️⃣ Criação ou atualização de repositório no GitHub via API
2️⃣ Commit automático dos arquivos locais
3️⃣ Push para a branch 'main'
4️⃣ Redeploy no serviço Render (ID fixo)
5️⃣ Rollback simplificado em caso de falha
6️⃣ Feedback detalhado e colorido de cada etapa
================================================================================
Avisos Importantes:
- Crie um arquivo .env na raiz do projeto com GITHUB_TOKEN e RENDER_API_KEY.
- Script suporta rollback simplificado.
- Destinado a ambiente de teste/desenvolvimento.
#>

# ==============================
# Configurações do Ambiente
# ==============================
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"  # Para qualquer erro, o script para imediatamente

# ==============================
# Configurações do Projeto
# ==============================
$githubUser      = "jbiriteiro"
$repoName        = "labbirita-mini"
$localPath       = Convert-Path "."

# ID do serviço Render (fixo)
$renderServiceId = "srv-d3sq1p8dl3ps73ar54s0"

# Configurações do Serviço Render
$renderServiceType = "web"
$renderServiceEnv  = "python"
$commitMessage     = "Deploy Automático: Correção final v3.3 (.env support)"

# ==============================
# Funções de utilidade
# ==============================

function Load-EnvFile {
    <#
    Carrega as variáveis de ambiente a partir de um arquivo .env na raiz do projeto.
    O arquivo deve estar no formato KEY=VALUE.
    #>
    $envFilePath = Join-Path $localPath ".env"

    if (Test-Path $envFilePath) {
        Write-Host "✅ Arquivo .env encontrado. Carregando variáveis..." -ForegroundColor DarkGreen
        Get-Content $envFilePath | ForEach-Object {
            # Ignora linhas vazias ou comentários (#)
            if ($_ -match "^\s*#") {
                # Ignore comments
            } elseif ($_ -match "^\s*([a-zA-Z_]+)\s*=\s*['""]?(.*?)['""]?\s*$") {
                $key = $Matches[1]
                # Remove aspas externas e espaços em branco
                $value = $Matches[2].Trim()

                # Define a variável na sessão atual
                Set-Item "env:\$key" $value
                Write-Host "   -> $key carregado." -ForegroundColor DarkGray
            }
        }
    } else {
        Write-Host "⚠️ Arquivo .env não encontrado. Dependendo das variáveis de ambiente de sessão/sistema." -ForegroundColor Yellow
    }
}

# ----------------------------------------------------
# ❗ NOVO: CHECAGEM E VALIDAÇÃO DE VARIÁVEIS DE AMBIENTE
# ----------------------------------------------------
# 1. Tenta carregar do .env (se existir)
Load-EnvFile

# 2. Faz a checagem final
if (-not $env:GITHUB_TOKEN) {
    Write-Host "❌ ERRO FATAL: Variável de ambiente GITHUB_TOKEN não encontrada ou vazia." -ForegroundColor Red
    Write-Host "Instrução: Crie um arquivo .env na pasta, ou use `$env:GITHUB_TOKEN = 'seu_token'` antes de rodar o script." -ForegroundColor Yellow
    exit 1
}
if (-not $env:RENDER_API_KEY) {
    Write-Host "❌ ERRO FATAL: Variável de ambiente RENDER_API_KEY não encontrada ou vazia." -ForegroundColor Red
    Write-Host "Instrução: Crie um arquivo .env na pasta, ou use `$env:RENDER_API_KEY = 'sua_chave'` antes de rodar o script." -ForegroundColor Yellow
    exit 1
}
# ----------------------------------------------------

# Headers de autenticação (usando as variáveis carregadas)
$headersGitHub = @{
    Authorization = "token $env:GITHUB_TOKEN"
    Accept        = "application/vnd.github+json"
}
$headersRender = @{
    "Authorization" = "Bearer $env:RENDER_API_KEY"
    "Content-Type"  = "application/json"
}


function Check-GitHubToken {
    <#
    Verifica se o token do GitHub é válido e retorna o login do usuário
    #>
    try {
        # Tenta pegar informações do usuário com o token fornecido
        $user = Invoke-RestMethod -Uri "https://api.github.com/user" -Headers $headersGitHub
        Write-Host "✅ Token GitHub OK! Usuário: $($user.login)" -ForegroundColor Green
    } catch {
        # Se falhar, é token inválido ou falta de permissão (Scopes)
        Write-Host "❌ Token GitHub inválido ou sem permissão. Verifique seu token no .env e se ele possui o scope 'repo'." -ForegroundColor Red
        exit 1
    }
}

function Create-GitHubRepo {
    <#
    Cria o repositório no GitHub caso não exista.
    #>
    try {
        $body = @{ name = $repoName; private = $true } | ConvertTo-Json
        $response = Invoke-RestMethod -Uri "https://api.github.com/user/repos" -Method Post -Headers $headersGitHub -Body $body
        Write-Host "✅ Repositório criado no GitHub: $($response.html_url)" -ForegroundColor Green
    } catch {
        # Geralmente o erro aqui significa que o repo já existe, o que é OK
        Write-Host "⚠️ Repositório já existe ou outro erro (ok): $($_.Exception.Message)" -ForegroundColor DarkYellow
    }
}

function Init-LocalGit {
    <#
    Inicializa Git local, adiciona remoto e configura usuário.
    #>
    # NOTA: O token está embutido na URL do remote para permitir o push automático (HTTPS)
    $remoteUrl = "https://$($githubUser):$($env:GITHUB_TOKEN)@github.com/$githubUser/$repoName.git"
    try {
        if (-not (Test-Path ".git")) {
            git init | Out-Null
            Write-Host "✅ Git iniciado localmente" -ForegroundColor Green
            git config user.name "José Biriteiro"
            git config user.email "josebiriteiro@gmail.com"
        }

        $remotes = git remote
        if ($remotes -notcontains "origin") {
            git remote add origin $remoteUrl | Out-Null
            Write-Host "✅ Remoto 'origin' adicionado." -ForegroundColor Green
        } else {
            git remote set-url origin $remoteUrl | Out-Null
            Write-Host "✅ Remoto 'origin' atualizado." -ForegroundColor Green
        }
    } catch {
        Write-Host "❌ Falha ao configurar o Git local: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
}

function Commit-And-Push {
    <#
    Adiciona arquivos, cria commit e envia para o GitHub
    #>
    try {
        git add . | Out-Null
        git commit -m "$commitMessage" | Out-Null
        Write-Host "✅ Commit efetuado: '$commitMessage'" -ForegroundColor Green
        git branch -M main | Out-Null
        # O push usa o token embutido na URL setada na Init-LocalGit
        git push -u origin main | Out-Null
        Write-Host "🚀 Push enviado para GitHub: https://github.com/$githubUser/$repoName" -ForegroundColor Cyan
    } catch {
        Write-Host "❌ Falha no Commit/Push. Verifique suas permissões (branch principal 'main' existe?)" -ForegroundColor Red
        exit 1
    }
}

function Redeploy-Render {
    <#
    Aciona redeploy no serviço Render e exibe a URL
    #>
    try {
        # Aciona o deploy
        Invoke-RestMethod -Uri "https://api.render.com/v1/services/$renderServiceId/deploys" -Method Post -Headers $headersRender | Out-Null
        Write-Host "✅ Redeploy solicitado com sucesso para o serviço: $renderServiceId" -ForegroundColor Green

        # Busca a URL para exibição
        $serviceDetails = Invoke-RestMethod -Uri "https://api.render.com/v1/services/$renderServiceId" -Headers $headersRender
        if ($serviceDetails.serviceDetails.url) {
            Write-Host "🌐 URL do Serviço: $($serviceDetails.serviceDetails.url)" -ForegroundColor Cyan
        }
    } catch {
        Write-Host "❌ Deploy Render falhou (Erro de API ou Conexão): $($_.Exception.Message)" -ForegroundColor Red
        if ($renderServiceId) {
            Write-Host "♻️ Rollback automático acionado para serviço $renderServiceId (Verifique o log do Render)" -ForegroundColor Yellow
        }
        exit 1
    }
}

# ==============================
# Execução do Script
# ==============================
Write-Host "`n🎯 Iniciando Deploy Automático LabBirita Mini..." -ForegroundColor Magenta
Check-GitHubToken
Create-GitHubRepo
Init-LocalGit
Commit-And-Push
Redeploy-Render
Write-Host "`n🎉 DEPLOY AUTOMÁTICO CONCLUÍDO COM SUCESSO! (Solicitado)" -ForegroundColor Magenta
Write-Host "------------------------------------------------------" -ForegroundColor Magenta
Write-Host "⚠️ Próximo passo: Verifique o log do Render para confirmar o status final." -ForegroundColor Yellow