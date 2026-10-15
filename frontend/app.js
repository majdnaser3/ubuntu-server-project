
const registerForm = document.getElementById("register-form");

registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const username = document.getElementById("register-username").value;
    const password = document.getElementById("register-password").value;

    try {
        const response = await fetch("/register", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();

        if (!response.ok) {
            document.getElementById("register-message").textContent =
                data.detail || "Registration failed.";
            return;
        }

        document.getElementById("register-message").textContent =
            "Account created successfully!";
        registerForm.reset();

    } catch (error) {
        document.getElementById("register-message").textContent =
            "Could not connect to the server.";
        console.error(error);
    }
});



const loginForm = document.getElementById("login-form");

loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;

    try {
        const response = await fetch("/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();

        if (!response.ok) {
            document.getElementById("login-message").textContent =
                data.detail || "Login failed.";
            return;
        }

        sessionStorage.setItem("access_token", data.access_token);

        document.getElementById("login-message").textContent =
            "Login successful!";
        loginForm.reset();

    } catch (error) {
        document.getElementById("login-message").textContent =
            "Could not connect to the server.";
        console.error(error);
    }
});
