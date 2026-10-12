document.addEventListener('DOMContentLoaded', () => {
    const cart = new Map();
    const buttons = new Map(
        [...document.querySelectorAll('.add-to-cart-btn')].map(button => [button.dataset.id, button])
    );
    const sidebar = document.getElementById('cartSidebar');
    const overlay = document.getElementById('cartOverlay');
    const checkout = document.getElementById('checkoutForm');
    const orderButton = document.getElementById('placeOrderButton');
    const csrfToken = checkout.querySelector('[name=csrfmiddlewaretoken]').value;
    let submitting = false;

    function closeCart() {
        sidebar.classList.remove('open');
        overlay.classList.remove('show');
    }

    function openCart() {
        renderCart();
        sidebar.classList.add('open');
        overlay.classList.add('show');
    }

    window.toggleCart = () => sidebar.classList.contains('open') ? closeCart() : openCart();
    overlay.addEventListener('click', closeCart);
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape') closeCart();
    });

    function updateButton(id) {
        const button = buttons.get(id);
        const stock = Number(button.dataset.stock);
        const inCart = cart.get(id)?.quantity || 0;
        button.disabled = stock <= inCart;
        button.textContent = stock === 0 ? 'Out of Stock' : stock <= inCart ? 'All stock in cart' : 'Add to Cart';
        button.classList.toggle('btn-success', !button.disabled);
        button.classList.toggle('btn-secondary', button.disabled);
        button.closest('.card-body').querySelector('.stock-count').textContent = `Stock: ${stock}`;
    }

    function renderCart() {
        const container = document.getElementById('cartItems');
        container.replaceChildren();
        let total = 0;
        for (const [id, item] of cart) {
            total += item.price * item.quantity;
            const row = document.createElement('div');
            row.className = 'cart-item';
            const name = document.createElement('strong');
            name.textContent = item.name;
            const quantity = document.createElement('input');
            quantity.type = 'number';
            quantity.min = '1';
            quantity.max = buttons.get(id).dataset.stock;
            quantity.value = item.quantity;
            quantity.style.width = '70px';
            quantity.setAttribute('aria-label', `Quantity for ${item.name}`);
            quantity.addEventListener('change', () => {
                const value = Number(quantity.value);
                if (Number.isInteger(value) && value >= 1 && value <= Number(quantity.max)) {
                    item.quantity = value;
                    updateButton(id);
                    renderCart();
                } else {
                    quantity.value = item.quantity;
                }
            });
            const remove = document.createElement('button');
            remove.type = 'button';
            remove.className = 'btn btn-sm btn-danger ms-2';
            remove.textContent = 'Remove';
            remove.addEventListener('click', () => {
                cart.delete(id);
                updateButton(id);
                renderCart();
            });
            row.append(name, document.createElement('br'), `$${item.price.toFixed(2)} × `, quantity, remove);
            container.append(row);
        }
        const summary = document.createElement('p');
        summary.className = 'cart-summary';
        summary.textContent = cart.size ? `Total: $${total.toFixed(2)}` : 'Your cart is empty.';
        container.append(summary);
        orderButton.disabled = submitting || cart.size === 0;
    }

    async function postJSON(url, payload) {
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
            credentials: 'same-origin',
            body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || data.error || JSON.stringify(data));
        }
        return data;
    }

    for (const [id, button] of buttons) {
        button.addEventListener('click', () => {
            const stock = Number(button.dataset.stock);
            const item = cart.get(id);
            if ((item?.quantity || 0) >= stock) return;
            if (item) {
                item.quantity += 1;
            } else {
                cart.set(id, { name: button.dataset.name, price: Number(button.dataset.price), quantity: 1 });
            }
            updateButton(id);
            openCart();
        });
        postJSON(checkout.dataset.stockUrl, { id: Number(id) })
            .then(data => {
                button.dataset.stock = data.stock;
                // A stale stock snapshot must not leave an impossible quantity in the cart.
                const item = cart.get(id);
                if (item && item.quantity > data.stock) {
                    if (data.stock === 0) cart.delete(id);
                    else item.quantity = data.stock;
                }
                updateButton(id);
                renderCart();
            })
            .catch(error => console.error('Could not refresh stock:', error.message));
    }

    checkout.addEventListener('submit', async event => {
        event.preventDefault();
        if (submitting || cart.size === 0 || !checkout.reportValidity()) return;
        submitting = true;
        renderCart();
        try {
            const data = await postJSON(checkout.dataset.buyUrl, {
                email: document.getElementById('buyerEmail').value.trim(),
                cart: [...cart].map(([id, item]) => ({ id: Number(id), quantity: item.quantity }))
            });
            alert(data.message);
            window.location.reload();
        } catch (error) {
            alert(`Could not confirm the order: ${error.message}. If the connection failed, check stock before retrying.`);
            submitting = false;
            renderCart();
        }
    });
    renderCart();
});
