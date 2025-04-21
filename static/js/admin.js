document.addEventListener('DOMContentLoaded', function() {
    // Handle adding new user
    const saveUserBtn = document.getElementById('saveUser');
    if (saveUserBtn) {
        saveUserBtn.addEventListener('click', async function() {
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const role = document.getElementById('role').value;

            try {
                const response = await fetch('/api/users', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        username: username,
                        password: password,
                        role: role
                    })
                });

                if (response.ok) {
                    const result = await response.json();
                    alert('User added successfully!');
                    // Close modal and reset form
                    const modal = bootstrap.Modal.getInstance(document.getElementById('addUserModal'));
                    modal.hide();
                    document.getElementById('addUserForm').reset();
                    // Refresh the page to show updated data
                    window.location.reload();
                } else {
                    const error = await response.json();
                    alert(error.message || 'Failed to add user');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('An error occurred while adding the user');
            }
        });
    }

    // Auto-refresh orders every 30 seconds
    setInterval(() => {
        window.location.reload();
    }, 30000);
}); 