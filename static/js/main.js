document.addEventListener('DOMContentLoaded', function() {
    const orderForm = document.getElementById('orderForm');
    const orderStatusModal = new bootstrap.Modal(document.getElementById('orderStatusModal'));
    const submitButton = document.getElementById('submit-button');
    const quantityInput = document.getElementById('quantity');
    const totalAmountSpan = document.getElementById('totalAmount');
    const incrementBtn = document.getElementById('incrementBtn');
    const decrementBtn = document.getElementById('decrementBtn');
    const PRICE_PER_CUP = 25; // ₹25 per cup

    // Initialize Stripe
    const stripe = Stripe(STRIPE_PUBLISHABLE_KEY);

    // Handle quantity increment/decrement
    incrementBtn.addEventListener('click', () => {
        const currentValue = parseInt(quantityInput.value);
        if (currentValue < 100) {
            quantityInput.value = currentValue + 1;
            updateTotalAmount();
        }
    });

    decrementBtn.addEventListener('click', () => {
        const currentValue = parseInt(quantityInput.value);
        if (currentValue > 1) {
            quantityInput.value = currentValue - 1;
            updateTotalAmount();
        }
    });

    function updateTotalAmount() {
        const quantity = parseInt(quantityInput.value);
        const total = quantity * PRICE_PER_CUP;
        totalAmountSpan.textContent = total;
    }

    orderForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        submitButton.disabled = true;

        const name = document.getElementById('name').value;
        const phone = document.getElementById('phone').value;
        const quantity = parseInt(quantityInput.value);

        try {
            // Create a checkout session
            const response = await fetch('/create-checkout-session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    name: name,
                    phone: phone,
                    quantity: quantity
                })
            });

            const data = await response.json();

            if (data.error) {
                throw new Error(data.error);
            }

            // Redirect to Stripe Checkout
            const result = await stripe.redirectToCheckout({
                sessionId: data.sessionId
            });

            if (result.error) {
                throw new Error(result.error.message);
            }

        } catch (error) {
            console.error('Error:', error);
            alert(error.message || 'An error occurred. Please try again.');
            submitButton.disabled = false;
        }
    });
}); 