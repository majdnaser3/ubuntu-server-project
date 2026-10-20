
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

    await loadAdminUsers();

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
            item.className = "file-row";

            
            const fileInfo = document.createElement("div");
            fileInfo.className = "file-name";

            const nameText = document.createElement("div");
            nameText.className = "file-name-text";
            nameText.textContent = file.original_filename;
            nameText.title = file.original_filename;

            const sizeText = document.createElement("div");
            sizeText.className = "file-size";

            const size = file.size_bytes;
            const units = ["B", "KB", "MB", "GB", "TB"];
            let formattedSize = size;
            let unitIndex = 0;

            while (formattedSize >= 1024 && unitIndex < units.length - 1) {
                formattedSize /= 1024;
                unitIndex++;
            }

            sizeText.textContent =
                `${formattedSize.toFixed(2)} ${units[unitIndex]}`;

            fileInfo.append(nameText, sizeText);


            const actions = document.createElement("div");
            actions.className = "file-actions";

            const downloadButton = document.createElement("button");
            downloadButton.textContent = "Download";
            downloadButton.type = "button";
            downloadButton.className = "download-button";

            downloadButton.addEventListener("click", async () => {
                const currentToken = sessionStorage.getItem("access_token");

                try {
                    const downloadResponse = await fetch(
                        `/files/${file.id}/download-link`,
                        {
                            method: "POST",
                            headers: {
                                "Authorization": `Bearer ${currentToken}`
                            }
                        }
                    );

                    const downloadData = await downloadResponse.json();

                    if (!downloadResponse.ok) {
                        filesMessage.textContent =
                            downloadData.detail || "Download failed.";
                        return;
                    }

                    const downloadLink = document.createElement("a");
                    downloadLink.href = downloadData.download_url;
                    downloadLink.target = "_blank";
                    downloadLink.rel = "noopener";
                    document.body.appendChild(downloadLink);
                    downloadLink.click();
                    downloadLink.remove();
                } catch (error) {
                    filesMessage.textContent = "Could not download the file.";
                    console.error(error);
                }
            });

            const deleteButton = document.createElement("button");
            deleteButton.textContent = "Delete";
            deleteButton.type = "button";
            deleteButton.className = "delete-button";

            deleteButton.addEventListener("click", async () => {
                const confirmed = confirm(
                    `Are you sure you want to delete "${file.original_filename}"?`
                );

                if (!confirmed) return;

                const currentToken = sessionStorage.getItem("access_token");

                try {
                    const deleteResponse = await fetch(
                        `/files/${file.id}`,
                        {
                            method: "DELETE",
                            headers: {
                                "Authorization": `Bearer ${currentToken}`
                            }
                        }
                    );

                    const result = await deleteResponse.json();

                    if (!deleteResponse.ok) {
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

            actions.append(downloadButton, deleteButton);
            item.append(fileInfo, actions);
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

    
    let storageData;

    try {
        const storageResponse = await fetch("/files/storage", {
            headers: {
                "Authorization": `Bearer ${token}`
            }
        });

        storageData = await storageResponse.json();

        if (!storageResponse.ok) {
            uploadMessage.textContent =
                storageData.detail || "Could not check your upload limits.";
            return;
        }
    } catch (error) {
        uploadMessage.textContent =
            "Could not check your upload limits. Please try again.";
        console.error(error);
        return;
    }

    const effectiveFileLimit = Math.min(
        storageData.max_upload_size_bytes,
        storageData.server_max_upload_size_bytes
    );

    if (file.size > effectiveFileLimit) {
        const limitMiB = (effectiveFileLimit / (1024 * 1024)).toFixed(2);

        uploadMessage.textContent =
            `File is too large. Your maximum single-file upload is ${limitMiB} MiB.`;
        return;
    }

    if (file.size > storageData.remaining_bytes) {
        const remainingMiB =
            (storageData.remaining_bytes / (1024 * 1024)).toFixed(2);

        uploadMessage.textContent =
            `Not enough storage space. You have ${remainingMiB} MiB remaining.`;
        return;
    }


    if (file.size > storageData.remaining_bytes) {
        const remainingMiB =
            (storageData.remaining_bytes / (1024 * 1024)).toFixed(2);

        uploadMessage.textContent =
            `Not enough storage space. You have ${remainingMiB} MiB remaining.`;
        return;
    }


    const formData = new FormData();
    formData.append("uploaded_file", file);

    
    const progressBar = document.getElementById("upload-progress");
    const progressText = document.getElementById("upload-progress-text");

    const xhr = new XMLHttpRequest();

    progressBar.value = 0;
    progressBar.hidden = false;
    progressText.hidden = false;
    progressText.textContent = "Starting upload...";

    xhr.open("POST", "/files/upload");
    xhr.setRequestHeader("Authorization", `Bearer ${token}`);

    xhr.upload.addEventListener("progress", (event) => {
        if (event.lengthComputable) {
            const percent = Math.round(
                (event.loaded / event.total) * 100
            );

            progressBar.value = percent;
            progressText.textContent = `Uploading: ${percent}%`;
        }
    });

    xhr.addEventListener("load", async () => {
        let data = {};

        try {
            data = JSON.parse(xhr.responseText);
        } catch {
            data = {};
        }

        if (xhr.status < 200 || xhr.status >= 300) {
            uploadMessage.textContent = data.detail || "Upload failed.";
            progressBar.hidden = true;
            progressText.hidden = true;
            return;
        }

        progressBar.value = 100;
        progressText.textContent = "Upload complete!";
        uploadMessage.textContent = "File uploaded successfully!";

        uploadForm.reset();
        await loadFiles();

        setTimeout(() => {
            progressBar.hidden = true;
            progressText.hidden = true;
        }, 1500);
    });

    xhr.addEventListener("error", () => {
        uploadMessage.textContent = "Could not connect to the server.";
        progressBar.hidden = true;
        progressText.hidden = true;
    });

    xhr.send(formData);

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


const setupButton = document.getElementById("show-setup");
const setupSection = document.getElementById("setup-section");
const setupForm = document.getElementById("setup-form");
const setupMessage = document.getElementById("setup-message");

async function checkSetupStatus() {
    try {
        const response = await fetch("/setup/status");
        if (!response.ok) return;

        const status = await response.json();

        setupButton.hidden = !status.setup_required;

        if (status.setup_required) {
            setupButton.addEventListener("click", () => {
                loginSection.hidden = true;
                registerSection.hidden = true;
                setupSection.hidden = false;
            });
        }
    } catch (error) {
        console.error("Could not check initial setup status:", error);
    }
}

setupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const setup_token = document.getElementById("setup-token").value;
    const username = document.getElementById("setup-username").value.trim();
    const password = document.getElementById("setup-password").value;

    setupMessage.textContent = "Creating administrator...";

    try {
        const response = await fetch("/setup/admin", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ setup_token, username, password })
        });

        const data = await response.json();

        if (!response.ok) {
            setupMessage.textContent =
                data.detail || "Administrator setup failed.";
            return;
        }

        setupForm.reset();
        setupSection.hidden = true;
        setupButton.hidden = true;
        loginSection.hidden = false;
        registerSection.hidden = true;

        document.getElementById("username").value = username;
        document.getElementById("login-message").textContent =
            "Administrator created. Please log in.";

    } catch (error) {
        setupMessage.textContent = "Could not connect to the server.";
        console.error(error);
    }
});

checkSetupStatus();


async function loadAdminUsers() {
    const section = document.getElementById("admin-section");
    const usersList = document.getElementById("admin-users-list");
    const message = document.getElementById("admin-message");
    const token = sessionStorage.getItem("access_token");

    section.hidden = true;
    usersList.replaceChildren();

    if (!token) return;

    try {
        const response = await fetch("/admin/users", {
            headers: {
                "Authorization": `Bearer ${token}`
            }
        });

        if (!response.ok) {
            if (response.status !== 401 && response.status !== 403) {
                message.textContent = "Could not load administrator settings.";
            }
            return;
        }

        const users = await response.json();
        section.hidden = false;
        message.textContent = "";

        for (const user of users) {
            const card = document.createElement("div");
            card.className = "admin-user-card";

            const heading = document.createElement("h3");
            heading.textContent = `${user.username} (ID: ${user.id})`;

            const usage = document.createElement("p");
            const usedGB = user.storage_used_bytes / 1_000_000_000;
            const quotaGB = user.storage_quota_bytes / 1_000_000_000;

            usage.textContent =
                `Storage used: ${usedGB.toFixed(3)} GB of ${quotaGB.toFixed(3)} GB · Files: ${user.file_count}`;

            const form = document.createElement("form");

            const quotaLabel = document.createElement("label");
            quotaLabel.textContent = "Storage quota (GB)";
            const quotaInput = document.createElement("input");
            quotaInput.type = "number";
            quotaInput.min = "0.01";
            quotaInput.step = "0.01";
            quotaInput.required = true;
            quotaInput.value = quotaGB;

            const uploadLabel = document.createElement("label");
            uploadLabel.textContent = "Maximum single-file upload (MiB)";
            const uploadInput = document.createElement("input");
            uploadInput.type = "number";
            uploadInput.min = "1";
            uploadInput.step = "1";
            uploadInput.required = true;
            uploadInput.value =
                user.max_upload_size_bytes / (1024 * 1024);

            const saveButton = document.createElement("button");
            saveButton.type = "submit";
            saveButton.textContent = "Save limits";

            const status = document.createElement("p");
            status.setAttribute("role", "status");

            quotaLabel.appendChild(quotaInput);
            uploadLabel.appendChild(uploadInput);
            form.append(quotaLabel, uploadLabel, saveButton, status);

            form.addEventListener("submit", async (event) => {
                event.preventDefault();
                saveButton.disabled = true;
                status.textContent = "Saving...";

                const storageQuota = Number(quotaInput.value);
                const maxUploadMiB = Number(uploadInput.value);

                if (
                    !Number.isFinite(storageQuota) ||
                    !Number.isFinite(maxUploadMiB) ||
                    storageQuota <= 0 ||
                    maxUploadMiB <= 0
                ) {
                    status.textContent = "Enter valid positive limits.";
                    saveButton.disabled = false;
                    return;
                }

                try {
                    const updateResponse = await fetch(
                        `/admin/users/${user.id}/limits`,
                        {
                            method: "PATCH",
                            headers: {
                                "Authorization": `Bearer ${token}`,
                                "Content-Type": "application/json"
                            },
                            body: JSON.stringify({
                                storage_quota_bytes:
                                    Math.round(storageQuota * 1_000_000_000),
                                max_upload_size_bytes:
                                    Math.round(maxUploadMiB * 1024 * 1024)
                            })
                        }
                    );

                    const result = await updateResponse.json();

                    if (!updateResponse.ok) {
                        status.textContent =
                            result.detail || "Could not save limits.";
                        return;
                    }

                    status.textContent = "Limits saved successfully.";
                    await loadAdminUsers();
                } catch (error) {
                    status.textContent = "Could not connect to the server.";
                    console.error(error);
                } finally {
                    saveButton.disabled = false;
                }
            });

            card.append(heading, usage, form);
            usersList.appendChild(card);
        }
    } catch (error) {
        message.textContent = "Could not load administrator settings.";
        console.error(error);
    }
}
