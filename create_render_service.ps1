# =====================================================
# Criar Web Service no Render via API (Full Automático)
# =====================================================

# -----------------------------
# CONFIGURAÇÕES
# -----------------------------
$renderApiKey = $env:RENDER_API_KEY       # Use variável de ambiente para segurança
$serviceName = "labbirita-mini"           # Nome do serviço no Render
$repoUrl     = "https://github.com/jbiriteiro/labbirita-mini.git"  # URL do repo GitHub
$branch      = "main"                     # Branch a usar

# Headers para API do Render
$headers = @{
    "Authorization" = "Bearer $renderApiKey"
    "Content-Type"  = "application/json"
}

# Body para criar Web Service
$body = @{
    name         = $serviceName
    type         = "web_service"
    environment  = "python"
    repo         = $repoUrl
    branch       = $branch
    buildCommand = "pip install -r requirements.txt"
    startCommand = "gunicorn app:app --bind 0.0.0.0:\$PORT"
    plan         = "free"
} | ConvertTo-Json -Depth 10

# -----------------------------
# CRIAR WEB SERVICE
# -----------------------------
try {
    $response = Invoke-RestMethod -Uri "https://api.render.com/v1/services" -Method Post -Headers $headers -Body $body
    Write-Host "✅ Web Service criado no Render: $($response.serviceDetails.url)"
} catch {
    Write-Error "❌ Erro ao criar Web Service: $($_.Exception.Message)"
}