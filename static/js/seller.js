document.addEventListener('DOMContentLoaded', function() {
    const ordersContainer = document.querySelector('.orders-container');

    // Function to update order status
    async function updateOrderStatus(orderId, status) {
        try {
            const response = await fetch('/update_order_status', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    order_id: orderId,
                    status: status
                })
            });

            const data = await response.json();
            if (data.success) {
                const orderCard = document.querySelector(`[data-order-id="${orderId}"]`);
                if (orderCard) {
                    const badge = orderCard.querySelector('.badge');
                    badge.textContent = status.charAt(0).toUpperCase() + status.slice(1);
                    badge.className = `badge bg-${status === 'ready' ? 'success' : 'warning'}`;
                    
                    const button = orderCard.querySelector('.mark-ready');
                    if (status === 'ready') {
                        button.disabled = true;
                        button.textContent = 'Order Ready';
                    }
                }
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Failed to update order status. Please try again.');
        }
    }

    // Add click event listeners to all "Mark as Ready" buttons
    ordersContainer.addEventListener('click', function(e) {
        if (e.target.classList.contains('mark-ready')) {
            const orderCard = e.target.closest('.order-card');
            const orderId = orderCard.dataset.orderId;
            updateOrderStatus(orderId, 'ready');
        }
    });

    // Auto-refresh orders every 30 seconds
    setInterval(async () => {
        try {
            const response = await fetch('/seller');
            const html = await response.text();
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const newOrdersContainer = doc.querySelector('.orders-container');
            ordersContainer.innerHTML = newOrdersContainer.innerHTML;
        } catch (error) {
            console.error('Error refreshing orders:', error);
        }
    }, 30000);
}); 