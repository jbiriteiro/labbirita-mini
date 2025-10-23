async function loadProducts(){
  const res = await fetch('/api/products');
  const data = await res.json();
  const container = document.getElementById('products');
  container.innerHTML = '';
  data.products.forEach(p=>{
    const div = document.createElement('div');
    div.className = 'product';
    div.innerHTML = `
      <div class="info">
        <div style="font-weight:600">${p.title}</div>
        <div class="price">R$ ${p.price.toFixed(2)}</div>
      </div>
      <button class="btn buy" data-id="${p.id}">Comprar</button>
    `;
    container.appendChild(div);
  });

  document.querySelectorAll('.buy').forEach(b=>{
    b.addEventListener('click', async (e)=>{
      const id = parseInt(e.target.dataset.id);
      const payload = { product_id: id, customer: { name: "Cliente Teste" } };
      const r = await fetch('/api/order', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const json = await r.json();
      showOrder(json);
    });
  });
}

function showOrder(json){
  document.getElementById('products').classList.add('hidden');
  document.getElementById('order-result').classList.remove('hidden');
  document.getElementById('order-json').textContent = JSON.stringify(json, null, 2);
  document.getElementById('back').onclick = ()=>{
    document.getElementById('products').classList.remove('hidden');
    document.getElementById('order-result').classList.add('hidden');
  };
}

loadProducts();