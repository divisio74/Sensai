const chat = document.getElementById("chat");
const form = document.getElementById("form");
const input = document.getElementById("input");
const send = document.getElementById("send");
const newChat = document.getElementById("new-chat");
const messages = [];

function scrollDown()
{
    chat.scrollTop = chat.scrollHeight;
}

function showUser(text)
{
    const div = document.createElement("div");

    div.className = "message user";
    div.textContent = text;
    chat.appendChild(div);
    scrollDown();
}

function renderText(container, text)
{
    const parts = text.split("```");

    parts.forEach((part, index) => {
        if (index % 2 === 1) {
            const pre = document.createElement("pre");
            pre.textContent = part.replace(/^\w*\n/, "");
            container.appendChild(pre);
        } else if (part.trim()) {
            const p = document.createElement("p");
            p.textContent = part.trim();
            container.appendChild(p);
        }
    });
}

function createAssistant()
{
    const div = document.createElement("div");

    div.className = "message assistant";
    div.innerHTML = '<div class="avatar">S</div><div class="content"></div>';
    chat.appendChild(div);
    scrollDown();
    return div.querySelector(".content");
}

function showTyping(content)
{
    content.innerHTML = '<div class="typing"><span></span><span></span><span></span></div>';
}

function showAnswer(content, answer)
{
    content.innerHTML = "";
    renderText(content, answer.text);
    scrollDown();
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const text = input.value.trim();
    if (!text)
        return;

    input.value = "";
    document.body.classList.remove("empty");
    showUser(text);
    messages.push({ role: "user", content: text });

    const content = createAssistant();
    showTyping(content);
    send.disabled = true;

    const answer = await askSensai();
    if (answer.error) {
        messages.pop();
        showAnswer(content, { text: answer.error });
    } else {
        messages.push({ role: "assistant", content: answer.text });
        showAnswer(content, answer);
    }
    send.disabled = false;
    input.focus();
});

newChat.addEventListener("click", () => {
    messages.length = 0;
    chat.innerHTML = "";
    document.body.classList.add("empty");
    input.focus();
});

async function askSensai()
{
    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ messages: messages }),
        });
        const data = await response.json();

        if (data.error)
            return { error: data.error };
        return { text: data.reply };
    } catch (error) {
        return { error: "The server is not reachable." };
    }
}
