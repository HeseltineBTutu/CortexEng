document.addEventListener('DOMContentLoaded', function () {
    AOS.init(); // Initialize AOS library

    // Form Elements
    const loginForm = document.getElementById("okta-login-form");
    const signUpContainer = document.querySelector(".signup-container");
    const confirmationMessage = document.getElementById("confirmationMessage");

    if (!signUpContainer) {
        console.error("Element with class 'signup-container' not found");
        return;
    }

    // Function to update the progress bar
    function updateProgressBar(step) {
        const progressFill = document.getElementById("progressFill");
        const totalSteps = 2;
        const progressPercent = (step / totalSteps) * 100;
        progressFill.style.width = `${progressPercent}%`;
    }
    updateProgressBar(1);

    loginForm.addEventListener("submit", async (event) => {
        event.preventDefault();

        const firstName = document.getElementById("firstName").value;
        const lastName = document.getElementById("lastName").value;
        const username = document.getElementById("username").value;
        const password = document.getElementById("password").value;
        const confirmPassword = document.getElementById('confirmPassword').value;

        // Client-side validation for confirm password
        if (password !== confirmPassword) {
            alert("Passwords do not match.");
            return;
        }

        try {
            // Register user in the backend
            const requestBody = {
                firstName,
                lastName,
                email: username,
                password
            };
            console.log("Sending request to /api/v1/signup with body:", requestBody);

            const response = await fetch('/api/v1/signup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody)
            });

            const contentType = response.headers.get('Content-Type');
            if (!contentType || !contentType.includes('application/json')) {
                throw new Error('Unexpected server response');
            }

            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.error || 'Registration failed');
            }

            // Store the user ID in localStorage
            localStorage.setItem('userId', result.user_id);
            console.log("User ID stored in localStorage:", result.user_id);

            // Show confirmation message and update progress bar
            confirmationMessage.classList.remove('hidden');
            updateProgressBar(2);

            // Wait for user to confirm email, then redirect to onboarding
            const checkEmailConfirmation = async () => {
                const checkResponse = await fetch('/api/v1/check_email_confirmation', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ email: username })
                });

                const checkResult = await checkResponse.json();
                if (checkResult.confirmed) {
                    window.location.href = '/api/v1/onboarding';
                } else {
                    setTimeout(checkEmailConfirmation, 5000); // Check again after 5 seconds
                }
            };
            checkEmailConfirmation();

        } catch (error) {
            console.error("Error during sign-in/up:", error);
            alert(error.message);  // Display a more informative error message to the user
        }
    });
});
