document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('login-form');
    loginForm.addEventListener('submit', handleLogin);

    function handleLogin(event) {
        event.preventDefault(); // Prevent the default form submission

        const emailInput = loginForm.querySelector('input[type="email"]');
        const passwordInput = loginForm.querySelector('input[type="password"]');
        const email = emailInput.value;
        const password = passwordInput.value;

        console.log('Email:', email);
        console.log('Password:', password);

        // Clear previous error messages
        const previousError = loginForm.querySelector('.error-message');
        if (previousError) {
            previousError.remove();
        }

        // Show loading indicator (optional)
        const loadingIndicator = document.createElement('div');
        loadingIndicator.textContent = 'Loading...';
        loadingIndicator.classList.add('loading-indicator');
        loginForm.appendChild(loadingIndicator);

        // Send an AJAX request to the server to authenticate the user
        fetch('/api/v1/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email, password })
        })
        .then(response => response.json())
        .then(data => {
            // Remove loading indicator
            loadingIndicator.remove();

            if (data.success) {
                // Redirect to the dashboard or another page
                window.location.href = data.redirect_url;
            } else {
                // Display an error message
                const errorContainer = document.createElement('div');
                errorContainer.textContent = data.error;
                errorContainer.classList.add('error-message');
                loginForm.appendChild(errorContainer);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            loadingIndicator.remove();
            
            // Display a general error message
            const errorContainer = document.createElement('div');
            errorContainer.textContent = 'An error occurred. Please try again.';
            errorContainer.classList.add('error-message');
            loginForm.appendChild(errorContainer);
        });
    }
});
