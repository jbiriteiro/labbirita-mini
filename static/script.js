document.addEventListener('DOMContentLoaded', async () => {
    const container = document.getElementById('produtos');
    const res = await fetch('/api/products');
    const produtos = await res.json();

    produtos.forEach(p => {
        const div = document.createElement('div');
        div.className = 'card';
        div.innerHTML = `
            <img src="${p.img}" alt="${p.nome}">
            <h3>${p.nome}</h3>
            <p>💰 R$ ${p.preco.toFixed(2)}</p>
            <button onclick="fazerPedido(${p.id})">Pedir Agora</button>
        `;
        container.appendChild(div);
    });
});

async function fazerPedido(id) {
    const resposta = await fetch('/api/order', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({produto_id: id})
    });

    const data = await resposta.json();
    alert(`✅ ${data.message}`);
}
