# app.py
"""
LabBirita Mini - Versão Profissional para Testes de Loja e Dropshipping
----------------------------------------------------------------------

Funcionalidades:
1️⃣ Servidor Flask para front-end e APIs
2️⃣ Produtos fake para testes
3️⃣ Endpoint de pedidos simulados com rastreio
4️⃣ Healthcheck
5️⃣ Logging de pedidos
6️⃣ Preparado para futura integração com gateway de pagamento/dropshipping

Autor: José Biriteiro
"""

from flask import Flask, jsonify, render_template, request
from datetime import datetime, timedelta
import random
import os
import logging

# ==============================
# Configurações básicas do Flask
# ==============================
app = Flask(
    __name__,
    static_folder="static",     # CSS, JS, imagens
    template_folder="templates" # HTML
)

# ==============================
# Logging de pedidos para testes
# ==============================
logging.basicConfig(
    filename="orders.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# ==============================
# Produtos de teste (mock)
# ==============================
PRODUCTS = [
    {"id": 1, "title": "Fone Bluetooth Sem Fio", "price": 99.0, "cost": 45.0},
    {"id": 2, "title": "Smartwatch Fitness Tracker", "price": 149.0, "cost": 70.0},
    {"id": 3, "title": "Suporte para Celular Carro", "price": 59.0, "cost": 20.0},
    {"id": 4, "title": "Carregador Portátil 10000mAh", "price": 139.0, "cost": 60.0},
    {"id": 5, "title": "Lente Macro para Câmera", "price": 59.0, "cost": 18.0},
]

# ==============================
# Rotas do Front-End
# ==============================
@app.route("/")
def index():
    """
    Página inicial da loja
    """
    return render_template("index.html")

# ==============================
# API para listar produtos
# ==============================
@app.route("/api/products", methods=["GET"])
def list_products():
    return jsonify({"products": PRODUCTS})

# ==============================
# API para criar pedido
# ==============================
@app.route("/api/order", methods=["POST"])
def create_order():
    """
    Recebe JSON:
    {
        "product_id": 1,
        "customer": {"name": "Fulano", "email": "fulano@mail.com"}
    }
    Retorna pedido simulado com rastreio.
    """
    data = request.get_json() or {}
    product_id = data.get("product_id")
    customer = data.get("customer", {})

    prod = next((p for p in PRODUCTS if p["id"] == product_id), None)
    if not prod:
        return jsonify({"error": "Produto não encontrado"}), 404

    # Simula rastreio
    order_id = f"LB{random.randint(100000,999999)}"
    shipped_in_days = random.choice([3, 5, 7, 14, 25])
    ship_date = datetime.utcnow().strftime("%Y-%m-%d")
    est_delivery = (datetime.utcnow() + timedelta(days=shipped_in_days)).strftime("%Y-%m-%d")
    
    tracking = {
        "order_id": order_id,
        "product": prod["title"],
        "price": prod["price"],
        "ship_date": ship_date,
        "estimated_delivery_date": est_delivery,
        "tracking_code": f"BR{random.randint(1000000,9999999)}",
        "status": "processing",
        "customer": customer
    }

    # Log do pedido
    logging.info(f"Pedido criado: {tracking}")

    return jsonify({"ok": True, "order": tracking})

# ==============================
# Healthcheck para Render/Monitoramento
# ==============================
@app.route("/health", methods=["GET"])
def healthcheck():
    return jsonify({"status": "OK"}), 200

# ==============================
# Inicialização do servidor
# ==============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)