const chat = document.getElementById("chat");
const form = document.getElementById("form");
const input = document.getElementById("input");
const send = document.getElementById("send");
const newChat = document.getElementById("new-chat");
const logout = document.getElementById("logout");
const context = document.getElementById("context");

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

function showContext(usage)
{
    if (!usage)
        return;
    const percent = Math.round(usage.used / usage.max * 100);
    context.textContent = `${usage.used} / ${usage.max} tokens (${percent}%)`;
    context.classList.toggle("full", percent >= 80);
}

let notes = JSON.parse(localStorage.getItem("notes") || "[]");
let shownCount = 0;

function saveNotes()
{
    localStorage.setItem("notes", JSON.stringify(notes));
}

function showNotes(position)
{
    notes.forEach((note) => {
        if (note.position === position) {
            if (note.text)
                showUser(note.text);
            showCommandOutput(note.output);
        }
    });
}

function showConversation(messages)
{
    chat.innerHTML = "";
    shownCount = messages.length;

    notes.forEach((note) => {
        note.position = Math.min(note.position, messages.length);
    });
    showNotes(0);
    messages.forEach((message, index) => {
        if (message.role === "user")
            showUser(message.display || message.content);
        else if (message.role === "assistant" && message.content)
            showAssistant(message.content);
        showNotes(index + 1);
    });
    document.body.classList.toggle("empty", messages.length === 0 && notes.length === 0);
}

async function sendText(text, onPiece)
{
    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: text }),
        });

        if (response.status === 401) {
            window.location.href = "/";
            return { output: "Not logged in.", messages: null };
        }
        if (response.headers.get("content-type").includes("application/json"))
            return await response.json();

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let streamed = "";
        while (true) {
            const { done, value } = await reader.read();
            if (done)
                break;
            const piece = decoder.decode(value, { stream: true });
            streamed += piece;
            onPiece(streamed);
        }

        const history = await fetch("/api/history");
        const data = await history.json();
        data.streamed = streamed;
        return data;
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
    const content = createAssistant();
    showTyping(content);
    send.disabled = true;

    const data = await sendText(text, (streamed) => {
        content.textContent = streamed;
        scrollDown();
    });
    if (data.streamed !== undefined && data.messages.length === shownCount)
        data.output = data.streamed;
    if (text === "/clear")
        notes = [];
    else if (data.output && data.messages) {
        const added = data.messages.length > shownCount;
        notes.push({ position: data.messages.length, text: added ? null : text, output: data.output });
    }
    saveNotes();

    if (data.messages) {
        showConversation(data.messages);
        showContext(data.context);
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
    saveNotes();
    showConversation(data.messages || []);
    showContext(data.context);
    input.focus();
});

logout.addEventListener("click", async () => {
    await fetch("/api/logout", { method: "POST" }).catch(() => {});
    localStorage.removeItem("notes");
    window.location.href = "/";
});

fetch("/api/history")
    .then((response) => response.json())
    .then((data) =>  {
        showConversation(data.messages);
        showContext(data.context);
    })
    .catch(() => {});
