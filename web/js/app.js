const chat = document.getElementById("chat");
const form = document.getElementById("form");
const input = document.getElementById("input");
const send = document.getElementById("send");
const newChat = document.getElementById("new-chat");

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

function showAssistant(text)
{
    const content = createAssistant();

    renderText(content, text);
    scrollDown();
}

function showCommandOutput(text)
{
    const content = createAssistant();

    content.classList.add("command");
    renderText(content, text);
    scrollDown();
}

let notes = [];

function showNotes(position)
{
    notes.forEach((note) => {
        if (note.position === position) {
            showUser(note.text);
            showCommandOutput(note.output);
        }
    });
}

function showConversation(messages)
{
    chat.innerHTML = "";
    notes.forEach((note) => {
        note.position = Math.min(note.position, messages.length);
    });
    showNotes(0);
    messages.forEach((message, index) => {
        if (message.role === "user")
            showUser(message.content);
        else if (message.role === "assistant")
            showAssistant(message.content);
        showNotes(index + 1);
    });
    document.body.classList.toggle("empty", messages.length === 0 && notes.length === 0);
}

async function sendText(text)
{
    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: text }),
        });
        return await response.json();
    } catch (error) {
        return { output: "The server is not reachable.", messages: null };
    }
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const text = input.value.trim();
    if (!text)
        return;

    input.value = "";
    document.body.classList.remove("empty");
    showUser(text);
    showTyping(createAssistant());
    send.disabled = true;

    const data = await sendText(text);
    if (text === "/clear")
        notes = [];
    else if (data.output && data.messages)
        notes.push({ position: data.messages.length, text: text, output: data.output });

    if (data.messages) {
        showConversation(data.messages);
    } else {
        chat.lastChild.remove();
        showCommandOutput(data.output);
    }
    send.disabled = false;
    input.focus();
});

newChat.addEventListener("click", async () => {
    const data = await sendText("/clear");
    notes = [];
    showConversation(data.messages || []);
    input.focus();
});

fetch("/api/history")
    .then((response) => response.json())
    .then((data) => showConversation(data.messages))
    .catch(() => {});
