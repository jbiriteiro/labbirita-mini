// Fetch produtos e renderiza cards
async function loadProducts() {
    const res = await fetch("/api/products");
    const data = await res.json();
    const container = document.getElementById("product-list");
    container.innerHTML = "";

    data.products.forEach(p => {
        const card = document.createElement("div");
        card.className = "product-card";
        card.innerHTML = `
            <h3>${p.title}</h3>
            <p>R$ ${p.price.toFixed(2)}</p>
            <button onclick="makeOrder(${p.id})">Comprar</button>
        `;
        container.appendChild(card);
    });
}

// Simula criação de pedido
async function makeOrder(productId) {
    const res = await fetch("/api/order", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_id: productId })
    });

    const data = await res.json();
    const result = document.getElementById("order-result");

    if (data.ok) {
        const order = data.order;
        result.innerHTML = `
            <h3>Pedido Criado!</h3>
            <p><strong>ID:</strong> ${order.order_id}</p>
            <p><strong>Produto:</strong> ${order.product}</p>
            <p><strong>Preço:</strong> R$ ${order.price.toFixed(2)}</p>
            <p><strong>Tracking:</strong> ${order.tracking_code}</p>
            <p><strong>Status:</strong> ${order.status}</p>
            <p><strong>Entrega Estimada:</strong> ${order.estimated_delivery_date}</p>
        `;
    } else {
        result.innerHTML = `<p style="color:red
