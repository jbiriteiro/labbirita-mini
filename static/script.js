/*
Arquivo: script.js
Função: Controla interações no front (carrinho, admin, mensagens)
Data: 23/10/2025
Autor: Gibão & GPT-5 🍻
*/

// Detecta se está no painel admin
const form = document.getElementById("productForm");
if (form) {
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    // Captura valores do formulário
    const productData = {
      name: document.getElementById("name").value,
      price: parseFloat(document.getElementById("price").value),
      description: document.getElementById("description").value,
      image: document.getElementById("image").value
    };

    // Envia pro backend (rota /admin/add)
    const response = await fetch("/admin/add", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(productData)
    });

    const msgDiv = document.getElementById("msg");

    if (response.ok) {
      msgDiv.textContent = "✅ Produto adicionado com sucesso!";
      msgDiv.style.color = "#00ff95";
      form.reset();
    } else {
      msgDiv.textContent = "❌ Erro ao adicionar produto!";
      msgDiv.style.color = "red";
    }

    setTimeout(() => { msgDiv.textContent = ""; }, 3000);
  });
}

// Função genérica pra adicionar ao carrinho
function addToCart(productName) {
  alert(`🍻 ${productName} foi adicionado ao carrinho! (Simulado)`);
}