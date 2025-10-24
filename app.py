# =============================================================================
# LabBirita Mini - App Flask (Produto + Checkout funcional - Simulado)
# Versão: 2025-10-24
#
# O que foi adicionado:
# - Rota /product/<id> para mostrar página de detalhe do produto
# - Formulário de checkout na página do produto (nome, email, tel, endereço)
# - Rota /checkout para processar formulário (server-side) e gerar pedido
# - Rota /order/<order_id> para página de confirmação
#
# Observações:
# - Persistência: data/orders.json (arquivo, simulação)
# - Admin e envio ao supplier continuam funcionando como antes
# - Mantenha ADMIN_TOKEN se quiser proteger admin
# - Lembre-se de ter a pasta 'data/' e permissões de escrita
# =============================================================================

from flask import Flask, jsonify, render_template, request, redirect, url_for, Response
from datetime import datetime, timedelta
import os, json, random, logging
from threading import Lock
import time

# ---------- CONFIG ----------
APP_NAME = "LabBirita Mini"
VERSION = "2025.10.24"
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
ORDERS_FILE = os.path.join(DATA_DIR, "orders.json")
LOG_FILE = os.path.join(BASE_DIR, "orders.log")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")  # opcional: definir para proteger admin
os.makedirs(DATA_DIR, exist_ok=True)

# Logging básico
logging.basicConfig(filename=LOG_FILE,
                    level=logging.INFO,
                    format="%(asctime)s | %(levelname)s | %(message)s")

file_lock = Lock()
app = Flask(__name__, static_folder="static", template_folder="templates")

# =========================
# Catálogo de produtos (exemplo — use teu catálogo completo aqui)
# =========================
PRODUCTS = [
    {"id": 1, "title": "Fone Bluetooth True Wireless X9", "price": 129.90,
     "cost": 42.00, "stock": 120, "supplier_url": "https://supplier.example.com/produto/x9",
     "image": "https://via.placeholder.com/600x400?text=Fone+X9",
     "short_desc": "Som estéreo, redução de ruído, estojo com carga rápida."},
    {"id": 2, "title": "Smartwatch Fitness Pro 2", "price": 249.90,
     "cost": 85.00, "stock": 80, "supplier_url": "https://supplier.example.com/produto/smartwatch-pro2",
     "image": "https://via.placeholder.com/600x400?text=Smartwatch+Pro+2",
     "short_desc": "Monitor cardíaco, GPS, 7 dias de bateria, resistente à água."},
    {"id": 3, "title": "Carregador Portátil 20000mAh Turbo", "price": 119.90,
     "cost": 30.00, "stock": 160, "supplier_url": "https://supplier.example.com/produto/powerbank-20000",
     "image": "https://via.placeholder.com/600x400?text=Powerbank+20000",
     "short_desc": "Dual USB-C + USB-A, carregamento rápido, display LED."},
    # ... adiciona o catálogo completo conforme já discutimos ...
]

# -------------------------
# Helpers de arquivo (thread-safe)
# -------------------------
def read_orders():
    """Lê orders.json e retorna lista (ou [] se não existir/corrompido)."""
    with file_lock:
        if not os.path.exists(ORDERS_FILE):
            return []
        try:
            with open(ORDERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

def write_orders(orders):
    """Escreve lista de pedidos em orders.json (thread-safe)."""
    with file_lock:
        with open(ORDERS_FILE, "w", encoding="utf-8") as f:
            json.dump(orders, f, ensure_ascii=False, indent=2)

def append_order(order):
    """Anexa um pedido novo ao arquivo."""
    orders = read_orders()
    orders.append(order)
    write_orders(orders)

def generate_tracking():
    """Gera tracking code simples."""
    return f"BR{random.randint(1000000,9999999)}"

def check_admin(token_provided):
    """Valida token admin. Se ADMIN_TOKEN vazio, libera (modo dev)."""
    if ADMIN_TOKEN == "":
        return True
    return token_provided and token_provided == ADMIN_TOKEN

# -------------------------
# Simulação de envio ao supplier (mantida)
# -------------------------
def simulate_send_to_supplier(supplier_url, order):
    """
    Simula um POST para o supplier.
    Retorna dict com o que seria a resposta do supplier (simulado).
    """
    time.sleep(0.5)  # delay simulado
    resp = {
        "ok": True,
        "supplier_order_id": f"S{random.randint(10000,99999)}",
        "estimated_ship_days": random.choice([1,2,3,4,5]),
        "message": "Pedido aceito pelo supplier (simulado)."
    }
    if random.random() < 0.04:
        resp["ok"] = False
        resp["message"] = "Supplier respondeu erro (simulado)."
    return resp

# =========================
# Rotas públicas / frontend
# =========================
@app.route("/")
def index():
    """Página inicial (lista de produtos)."""
    return render_template("index.html", products=PRODUCTS)

@app.route("/product/<int:product_id>")
def product_page(product_id):
    """
    Página de detalhe do produto.
    Renderiza templates/product.html com os dados do produto.
    Se produto não existir, retorna 404.
    """
    product = next((p for p in PRODUCTS if p["id"] == product_id), None)
    if not product:
        return Response("Produto não encontrado", status=404)
    return render_template("product.html", product=product)

@app.route("/api/products")
def api_products():
    """Retorna catálogo público de produtos (JSON)."""
    return jsonify({"products": PRODUCTS})

@app.route("/api/order", methods=["POST"])
def api_order():
    """
    API para criar pedido via JSON.
    Mantido para integração JS.
    """
    data = request.get_json(silent=True) or {}
    return _create_order_from_payload(data)

@app.route("/checkout", methods=["POST"])
def checkout_form():
    """
    Endpoint que processa o formulário de checkout (application/x-www-form-urlencoded).
    Espera campos: product_id, name, email, phone, address
    Redireciona para /order/<order_id> após criar o pedido.
    """
    form = request.form or {}
    product_id = form.get("product_id")
    # Validações básicas
    name = (form.get("name") or "").strip()
    email = (form.get("email") or "").strip()
    phone = (form.get("phone") or "").strip()
    address = (form.get("address") or "").strip()

    errors = []
    if not product_id:
        errors.append("Produto não informado.")
    if not name:
        errors.append("Nome é obrigatório.")
    if not email:
        errors.append("Email é obrigatório.")
    if not address:
        errors.append("Endereço é obrigatório.")

    if errors:
        # volta pro produto com mensagem de erro (simples)
        product = next((p for p in PRODUCTS if str(p["id"]) == str(product_id)), None)
        return render_template("product.html", product=product, form_errors=errors, form_data=form), 400

    payload = {
        "product_id": int(product_id),
        "customer": {
            "name": name,
            "email": email,
            "phone": phone,
            "address": address
        }
    }
    # cria pedido usando mesma lógica interna
    result = _create_order_from_payload(payload)
    if isinstance(result, tuple):
        # erro
        return result
    # result é Response JSON com order; extrai order_id e redireciona
    order_json = result.get_json()
    order_id = order_json.get("order", {}).get("order_id")
    if order_id:
        return redirect(url_for("order_confirm", order_id=order_id))
    else:
        return Response("Erro ao criar pedido", status=500)

@app.route("/order/<order_id>")
def order_confirm(order_id):
    """Página de confirmação do pedido."""
    orders = read_orders()
    order = next((o for o in orders if o.get("order_id") == order_id), None)
    if not order:
        return Response("Pedido não encontrado", status=404)
    return render_template("order.html", order=order)

# =========================
# Função interna de criação de pedido (reutilizada por /api/order e /checkout)
# =========================
def _create_order_from_payload(data):
    """
    Cria pedido a partir de payload (dict) com chaves:
      - product_id (int)
      - customer (dict) opcional
    Retorna Response JSON (201) com order ou (erro, status).
    """
    product_id = data.get("product_id")
    customer = data.get("customer", {})

    if not product_id:
        return jsonify({"ok": False, "error": "product_id é obrigatório"}), 400

    product = next((p for p in PRODUCTS if int(p["id"]) == int(product_id)), None)
    if not product:
        return jsonify({"ok": False, "error": "Produto não encontrado"}), 404

    now = datetime.utcnow()
    days = random.choice([3,5,7,14])
    order = {
        "order_id": f"LB{random.randint(100000,999999)}",
        "product_id": product["id"],
        "product_title": product["title"],
        "price": product["price"],
        "customer": customer,
        "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "ship_date": now.strftime("%Y-%m-%d"),
        "estimated_delivery_days": days,
        "estimated_delivery_date": (now + timedelta(days=days)).strftime("%Y-%m-%d"),
        "tracking_code": generate_tracking(),
        "status": "processing",
        "supplier": {
            "url": product.get("supplier_url"),
            "sent": False,
            "response": None
        },
        "history": [
            {"when": now.strftime("%Y-%m-%d %H:%M:%S"), "status": "processing"}
        ]
    }

    try:
        append_order(order)
        logging.info(f"Pedido criado {order['order_id']} produto:{product['id']} cliente:{customer.get('name','-')}")
    except Exception as e:
        logging.exception("Erro ao salvar pedido")
        return jsonify({"ok": False, "error": "Erro ao salvar pedido"}), 500

    return jsonify({"ok": True, "order": order}), 201

# =========================
# Admin UI + API (mantidos)
# =========================
@app.route("/admin")
def admin_ui():
    token = request.args.get("token", "")
    if not check_admin(token):
        return Response("Acesso não autorizado (admin token inválido).", status=401)
    return render_template("admin.html", app_name=APP_NAME, version=VERSION)

@app.route("/api/admin/orders", methods=["GET"])
def api_admin_orders():
    token = request.args.get("token") or request.headers.get("X-ADMIN-TOKEN", "")
    if not check_admin(token):
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    return jsonify({"orders": read_orders()})

@app.route("/api/admin/orders/<order_id>/send_supplier", methods=["POST"])
def api_admin_send_supplier(order_id):
    token = request.args.get("token") or request.headers.get("X-ADMIN-TOKEN", "")
    if not check_admin(token):
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    orders = read_orders()
    idx = next((i for i,o in enumerate(orders) if o.get("order_id")==order_id), None)
    if idx is None:
        return jsonify({"ok": False, "error": "order not found"}), 404

    order = orders[idx]
    product = next((p for p in PRODUCTS if p["id"]==order["product_id"]), None)
    supplier_url = product.get("supplier_url") if product else order.get("supplier",{}).get("url")

    supplier_resp = simulate_send_to_supplier(supplier_url, order)

    order["supplier"]["sent"] = True
    order["supplier"]["response"] = supplier_resp
    order["status"] = "sent_to_supplier" if supplier_resp.get("ok") else "supplier_error"
    order.setdefault("history", []).append({
        "when": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "status": order["status"],
        "note": supplier_resp.get("message")
    })

    orders[idx] = order
    write_orders(orders)
    logging.info(f"Pedido {order_id} enviado ao supplier. ok={supplier_resp.get('ok')}")
    return jsonify({"ok": True, "order": order, "supplier_response": supplier_resp})

@app.route("/api/admin/orders/<order_id>/status", methods=["POST"])
def api_admin_update_status(order_id):
    token = request.args.get("token") or request.headers.get("X-ADMIN-TOKEN", "")
    if not check_admin(token):
        return jsonify({"ok": False, "error": "unauthorized"}), 401

    body = request.get_json(silent=True) or {}
    new_status = body.get("status")
    if not new_status:
        return jsonify({"ok": False, "error": "status required"}), 400

    orders = read_orders()
    updated = False
    for o in orders:
        if o.get("order_id") == order_id:
            o["status"] = new_status
            o.setdefault("history", []).append({
                "when": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "status": new_status
            })
            updated = True
            break

    if not updated:
        return jsonify({"ok": False, "error": "order not found"}), 404

    write_orders(orders)
    logging.info(f"Pedido {order_id} atualizado para {new_status}")
    return jsonify({"ok": True, "order_id": order_id, "new_status": new_status})

# =========================
# Health
# =========================
@app.route("/health")
def health():
    return jsonify({"status":"OK", "timestamp": datetime.utcnow().isoformat()}), 200

# =========================
# Run server
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)