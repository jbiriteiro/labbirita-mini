# =========================================================
# LabBirita Mini - App Flask 1000 grau
# =========================================================
# Arquivo principal: app.py
# Framework: Flask
# Variável do Flask: app
# Funcionalidades:
# - Exibe página principal
# - API de produtos
# - API de pedidos simulados com rastreio
# - Healthcheck para Render
# =========================================================

from flask import Flask, jsonify, render_template, request
from datetime import datetime, timedelta
import random
import os

app = Flask(__name__, static_folder="static", template_folder="templates")

# Produtos de exemplo
PRODUCTS = [
    {"id": 1, "title": "Fone Bluetooth Sem Fio", "price": 99.0, "cost": 45.0},
    {"id": 2, "title": "Smartwatch Fitness Tracker", "price": 149.0, "cost": 70.0},
    {"id": 3, "title": "Suporte para Celular Carro", "price": 59.0, "cost": 20.0},
    {"id": 4, "title": "Carregador Portátil 10000mAh", "price": 139.0, "cost": 60.0},
    {"id": 5, "title": "Lente Macro para Câmera", "price": 59.0, "cost": 18.0},
]

# =========================
# Rotas da aplicação
# =========================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/products")
def products():
    return jsonify({"products": PRODUCTS})


@app.route("/api/order", methods=["POST"])
def order():
    data = request.get_json() or {}
    product_id = data.get("product_id")
    customer = data.get("customer", {})
    
    # Procura produto
    prod = next((p for p in PRODUCTS if p["id"] == product_id), None)
    if not prod:
        return jsonify({"error": "Produto não encontrado"}), 404

    # Simula pedido e rastreio
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
        "status": "processing"
    }

    return jsonify({"ok": True, "order": tracking})


@app.route("/health")
def health():
    return "OK", 200


# =========================
# Inicialização do servidor
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # Host 0.0.0.0 necessário pro Render
    app.run(host="0.0.0.0", port=port, debug=True)