const form = document.getElementById("login-form");
const email = document.getElementById("email");
const password = document.getElementById("password");
const persona = document.getElementById("persona");
const about = document.getElementById("about");
const error = document.getElementById("error");
const register = document.getElementById("register");

fetch("/api/personas")
    .then((response) => response.json())
    .then((data) => {
        data.personas.forEach((name) => {
            const option = document.createElement("option");
            option.value = name;
            option.textContent = name;
            persona.appendChild(option);
        });
    })
    .catch(() => {});

async function send(route)
{
    try {
        const response = await fetch(route, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                email: email.value.trim(),
                password: password.value,
                persona: persona.value,
                about: about.value,
            }),
        });
        if (response.ok) {
            localStorage.removeItem("notes");
            window.location.href = "/";
            return;
        }
        const data = await response.json();
        error.textContent = data.detail;
    } catch (e) {
        error.textContent = "The server is not reachable.";
    }
}

form.addEventListener("submit", (event) => {
    event.preventDefault();
    send("/api/login");
});

register.addEventListener("click", () => {
    if (form.reportValidity())
        send("/api/register");
});
