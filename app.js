const chatBox = document.getElementById("chat-box");
const questionInput = document.getElementById("question");
const askBtn = document.getElementById("ask-btn");
const statusBar = document.getElementById("status-bar");
const chatHistoryContainer = document.getElementById("chat-history");
const newChatBtn = document.getElementById("new-chat-btn");

let chats = JSON.parse(localStorage.getItem("sisiwenyewe_chats")) || [];
let currentChatId = null;
let isThinking = false;
let typingTimer = null;

function saveChats() {
    localStorage.setItem("sisiwenyewe_chats", JSON.stringify(chats));
}

function generateId() {
    return "chat_" + Date.now() + "_" + Math.floor(Math.random() * 10000);
}

function createNewChat() {
    const newChat = {
        id: generateId(),
        title: "New Chat",
        messages: [],
        createdAt: new Date().toISOString()
    };

    chats.unshift(newChat);
    currentChatId = newChat.id;
    saveChats();
    renderHistory();
    renderCurrentChat();
}

function getCurrentChat() {
    return chats.find(chat => chat.id === currentChatId);
}

function renderHistory() {
    chatHistoryContainer.innerHTML = "";

    if (chats.length === 0) {
        chatHistoryContainer.innerHTML = `<div class="empty-history">No chats yet.</div>`;
        return;
    }

    chats.forEach(chat => {
        const item = document.createElement("div");
        item.className = `history-item ${chat.id === currentChatId ? "active" : ""}`;

        const previewText = chat.messages.length
            ? chat.messages[0].text.slice(0, 60)
            : "Start a new conversation";

        item.innerHTML = `
            <div class="history-title">${chat.title}</div>
            <div class="history-preview">${previewText}</div>
            <div class="history-actions">
                <button class="delete-chat-btn" data-id="${chat.id}">Delete</button>
            </div>
        `;

        item.addEventListener("click", (e) => {
            if (e.target.classList.contains("delete-chat-btn")) return;
            currentChatId = chat.id;
            renderHistory();
            renderCurrentChat();
        });

        chatHistoryContainer.appendChild(item);
    });

    document.querySelectorAll(".delete-chat-btn").forEach(btn => {
        btn.addEventListener("click", (e) => {
            e.stopPropagation();
            deleteChat(btn.dataset.id);
        });
    });
}

function renderCurrentChat() {
    const currentChat = getCurrentChat();
    chatBox.innerHTML = "";

    if (!currentChat || currentChat.messages.length === 0) {
        chatBox.innerHTML = `
            <div class="welcome-card">
                <div class="welcome-icon">🧠</div>
                 <p class="welcome-text">
                    Ask anything from our CBRN knowledge base.
                </p>
                <div class="prompt-chip-wrap">
                    <button class="prompt-chip" onclick="fillPrompt('What is anthrax?')">What is anthrax?</button>
                    <button class="prompt-chip" onclick="fillPrompt('Summarise biological agents')">Biological agents</button>
                    <button class="prompt-chip" onclick="fillPrompt('What does the respiratory protection handbook say?')">Respiratory protection</button>
                    <button class="prompt-chip" onclick="fillPrompt('Explain emergency response guidance')">Emergency response</button>
                </div>
            </div>
        `;
        return;
    }

    currentChat.messages.forEach(message => {
        addMessageToUI(message.role, message.text, false);
    });

    chatBox.scrollTop = chatBox.scrollHeight;
}

function addMessageToUI(role, text, animate = false) {
    const row = document.createElement("div");
    row.className = `message-row ${role}`;

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";

    row.appendChild(bubble);
    chatBox.appendChild(row);
    chatBox.scrollTop = chatBox.scrollHeight;

    if (role === "bot" && animate) {
        typeText(bubble, text, 12);
    } else {
        bubble.textContent = text;
    }

    return bubble;
}

function typeText(element, text, speed = 12) {
    if (typingTimer) {
        clearInterval(typingTimer);
        typingTimer = null;
    }

    let i = 0;
    element.textContent = "";

    typingTimer = setInterval(() => {
        element.textContent += text.charAt(i);
        i += 1;
        chatBox.scrollTop = chatBox.scrollHeight;

        if (i >= text.length) {
            clearInterval(typingTimer);
            typingTimer = null;
        }
    }, speed);
}

function updateAskButton() {
    if (isThinking) {
        askBtn.textContent = "Stop";
        askBtn.classList.add("stop-mode");
    } else {
        askBtn.textContent = "Ask";
        askBtn.classList.remove("stop-mode");
    }
}

function startThinking() {
    isThinking = true;
    statusBar.classList.remove("hidden");
    updateAskButton();
}

function stopThinking() {
    isThinking = false;
    statusBar.classList.add("hidden");
    updateAskButton();
}

function deleteChat(chatId) {
    chats = chats.filter(chat => chat.id !== chatId);

    if (currentChatId === chatId) {
        currentChatId = chats.length ? chats[0].id : null;
    }

    saveChats();
    renderHistory();
    renderCurrentChat();

    if (!currentChatId) {
        createNewChat();
    }
}

async function sendMessage() {
    const question = questionInput.value.trim();
    if (!question || isThinking) return;

    const currentChat = getCurrentChat();
    if (!currentChat) return;

    if (currentChat.messages.length === 0) {
        currentChat.title = question.length > 28 ? question.slice(0, 28) + "..." : question;
    }

    currentChat.messages.push({
        role: "user",
        text: question
    });

    saveChats();
    renderHistory();
    renderCurrentChat();
    questionInput.value = "";
    startThinking();

    try {
        const response = await fetch("https://hearts-openings-tobacco-descriptions.trycloudflare.com/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                question,
                history: currentChat.messages.slice(-6)
            })
        });

        const data = await response.json();
        const botText = data.answer || "Sorry, I can’t answer that at the moment. Please check again in the next few days as my training and knowledge base continue to improve.";

        currentChat.messages.push({
            role: "bot",
            text: botText
        });

        saveChats();
        stopThinking();

        const bubble = addMessageToUI("bot", "", false);
        typeText(bubble, botText, 12);

    } catch (error) {
        const fallbackText = "Sorry, I can’t answer that at the moment. Please check again in the next few days as my training and knowledge base continue to improve.";

        currentChat.messages.push({
            role: "bot",
            text: fallbackText
        });

        saveChats();
        stopThinking();

        const bubble = addMessageToUI("bot", "", false);
        typeText(bubble, fallbackText, 12);
    }

    renderHistory();
}

function stopSearch() {
    stopThinking();
}

function fillPrompt(text) {
    questionInput.value = text;
    questionInput.focus();
}

askBtn.addEventListener("click", () => {
    if (isThinking) {
        stopSearch();
    } else {
        sendMessage();
    }
});

questionInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        if (isThinking) {
            stopSearch();
        } else {
            sendMessage();
        }
    }
});

newChatBtn.addEventListener("click", () => {
    createNewChat();
});

if (chats.length === 0) {
    createNewChat();
} else {
    currentChatId = chats[0].id;
    renderHistory();
    renderCurrentChat();
}

updateAskButton();