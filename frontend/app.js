
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

                
        const loginResponse = await fetch("/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ username, password })
        });

        const loginData = await loginResponse.json();

        if (!loginResponse.ok) {
            document.getElementById("register-message").textContent =
                "Account created, but automatic login failed. Please log in.";
            return;
        }

        sessionStorage.setItem("access_token", loginData.access_token);

        document.getElementById("auth-section").hidden = true;
        document.getElementById("files-section").hidden = false;

        registerForm.reset();
        await loadFiles();


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
            document.getElementById("auth-section").hidden = true;
            document.getElementById("files-section").hidden = false;
            loadFiles();
        loginForm.reset();

    } catch (error) {
        document.getElementById("login-message").textContent =
            "Could not connect to the server.";
        console.error(error);
    }
});


const loginSection = document.getElementById("login-section");
const registerSection = document.getElementById("register-section");

document.getElementById("show-login").addEventListener("click", () => {
    loginSection.hidden = false;
    registerSection.hidden = true;
});

document.getElementById("show-register").addEventListener("click", () => {
    loginSection.hidden = true;
    registerSection.hidden = false;
});



const filesList = document.getElementById("files-list");
const filesMessage = document.getElementById("files-message");

async function loadFiles() {
    const token = sessionStorage.getItem("access_token");

    if (!token) {
        filesMessage.textContent = "Please log in first.";
        return;
    }

    try {
        const response = await fetch("/files", {
            headers: {
                "Authorization": `Bearer ${token}`
            }
        });

        const data = await response.json();

        if (!response.ok) {
            filesMessage.textContent =
                data.detail || "Could not load files.";
            return;
        }

        filesList.replaceChildren();

        if (data.length === 0) {
            filesMessage.textContent = "No files uploaded yet.";
            return;
        }

        filesMessage.textContent = "";

        
    for (const file of data) {
        const item = document.createElement("li");
        const fileInfo = document.createElement("span");

        const size = file.size_bytes;
        const units = ["B", "KB", "MB", "GB", "TB"];
        let formattedSize = size;
        let unitIndex = 0;

        while (formattedSize >= 1024 && unitIndex < units.length - 1) {
            formattedSize /= 1024;
            unitIndex++;
        }

        fileInfo.textContent =
            `${file.original_filename} (${formattedSize.toFixed(2)} ${units[unitIndex]})`;

        
    item.appendChild(fileInfo);

    const downloadButton = document.createElement("button");
    downloadButton.textContent = "Download";
    downloadButton.type = "button";

    downloadButton.addEventListener("click", async () => {
        const token = sessionStorage.getItem("access_token");

        try {
            const response = await fetch(`/files/${file.id}/download`, {
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            });

            if (!response.ok) {
                filesMessage.textContent = "Download failed.";
                return;
            }

            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");

            link.href = url;
            link.download = file.original_filename;
            document.body.appendChild(link);
            link.click();
            link.remove();

            setTimeout(() => URL.revokeObjectURL(url), 1000);
        } catch (error) {
            filesMessage.textContent = "Could not download the file.";
            console.error(error);
        }
    });

    item.appendChild(downloadButton);
    
    const deleteButton = document.createElement("button");
    deleteButton.textContent = "Delete";
    deleteButton.type = "button";

    deleteButton.addEventListener("click", async () => {
        const confirmed = confirm(
            `Are you sure you want to delete "${file.original_filename}"?`
        );

        if (!confirmed) return;

        const token = sessionStorage.getItem("access_token");

        try {
            const response = await fetch(`/files/${file.id}`, {
                method: "DELETE",
                headers: {
                    "Authorization": `Bearer ${token}`
                }
            });

            const result = await response.json();

            if (!response.ok) {
                filesMessage.textContent =
                    result.detail || "Could not delete the file.";
                return;
            }

            filesMessage.textContent = "File deleted successfully.";
            await loadFiles();
        } catch (error) {
            filesMessage.textContent = "Could not connect to the server.";
            console.error(error);
        }
    });

    item.appendChild(deleteButton);

    filesList.appendChild(item);

    }

    } catch (error) {
        filesMessage.textContent = "Could not connect to the server.";
        console.error(error);
    }
}

document.getElementById("load-files").addEventListener("click", loadFiles);


const uploadForm = document.getElementById("upload-form");
const fileInput = document.getElementById("file-input");
const uploadMessage = document.getElementById("upload-message");

uploadForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const token = sessionStorage.getItem("access_token");
    const file = fileInput.files[0];

    if (!token || !file) {
        uploadMessage.textContent = "Log in and select a file first.";
        return;
    }

    const formData = new FormData();
    formData.append("uploaded_file", file);

    try {
        const response = await fetch("/files/upload", {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${token}`
            },
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            uploadMessage.textContent =
                data.detail || "Upload failed.";
            return;
        }

        uploadMessage.textContent = "File uploaded successfully!";
        uploadForm.reset();
        await loadFiles();

    } catch (error) {
        uploadMessage.textContent = "Could not connect to the server.";
        console.error(error);
    }
});



window.addEventListener("DOMContentLoaded", () => {
    if (sessionStorage.getItem("access_token")) {
        document.getElementById("auth-section").hidden = true;
        document.getElementById("register-section").hidden = true;
        document.getElementById("files-section").hidden = false;

        loadFiles();
    }
});



document.getElementById("logout-button").addEventListener("click", () => {
    sessionStorage.removeItem("access_token");

    document.getElementById("files-section").hidden = true;
    document.getElementById("auth-section").hidden = false;
    document.getElementById("login-section").hidden = false;
    document.getElementById("register-section").hidden = true;

    document.getElementById("login-message").textContent = "";
    document.getElementById("register-message").textContent = "";
    document.getElementById("files-message").textContent = "";
    document.getElementById("upload-message").textContent = "";
    document.getElementById("files-list").replaceChildren();
});


document.querySelectorAll(".toggle-password").forEach((button) => {
    button.addEventListener("click", () => {
        const input = document.getElementById(button.dataset.target);

        const isHidden = input.type === "password";
        input.type = isHidden ? "text" : "password";
        button.textContent = isHidden ? "Hide" : "Show";
    });
});
