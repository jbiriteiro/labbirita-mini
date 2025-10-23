from flask import Flask, render_template, jsonify, request
import datetime

app = Flask(__name__)

# ===============================
# 🛒 MOCK DE PRODUTOS (simulação)
# ===============================
PRODUTOS = [
    {"id": 1, "nome": "Cerveja Gelada", "preco": 7.99, "estoque": 120, "img": "https://i.imgur.com/pD5fXfG.png"},
    {"id": 2, "nome": "Vodka Absolut", "preco": 89.90, "estoque": 40, "img": "https://i.imgur.com/hLuvPjv.png"},
    {"id": 3, "nome": "Whisky Red Label", "preco": 139.90, "estoque": 25, "img": "https://i.imgur.com/jkHxQxZ.png"},
    {"id": 4, "nome": "Gin Tanqueray", "preco": 119.90, "estoque": 18, "img": "https://i.imgur.com/0C5FWvV.png"},
    {"id": 5, "nome": "Energético Red Bull", "preco": 11.50, "estoque": 200, "img": "https://i.imgur.com/tQ3M9m1.png"},
    {"id": 6, "nome": "Combo Biriteiro (Vodka + Energético)", "preco": 95.00, "estoque": 10, "img": "https://i.imgur.com/z7sTdut.png"},
]

# ===============================
# 🔹 Rotas
# ===============================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/products')
def get_products():
    return jsonify(PRODUTOS)

@app.route('/api/order', methods=['POST'])
def create_order():
    data = request.get_json()
    print(f"📦 Pedido recebido: {data}")  # Log básico
    return jsonify({
        "message": "Pedido recebido com sucesso!",
        "data": data,
        "timestamp": datetime.datetime.now().isoformat()
    })

@app.route('/health')
def health():
    return jsonify({"status": "ok", "timestamp": datetime.datetime.now().isoformat()})

# ===============================
# ⚙️ Execução local
# ===============================
if __name__ == '__main__':
    app.run(debug=True)
