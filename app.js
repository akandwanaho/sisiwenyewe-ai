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

    setTimeout(() => {
        questionInput.value = "";
        questionInput.focus();
        questionInput.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 50);
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

    if (!currentChat || currentChat.messages.length === 0) {
        chatBox.innerHTML = `
            <div class="welcome-card">
                <div class="welcome-icon">🧠</div>
                <p class="welcome-text">
                    Ask questions about CBRN threats, or analyze live sensor data and intelligence.
                </p>
                <div class="prompt-chip-wrap">
                    <button class="prompt-chip" onclick="fillPrompt('What is anthrax?')">What is anthrax?</button>
                    <button class="prompt-chip" onclick="fillPrompt('Summarise biological agents')">Summarise biological agents</button>
                    <button class="prompt-chip" onclick="fillPrompt('Show me the latest sensor data and current readings')">Live Sensor Data</button>
                    <button class="prompt-chip" onclick="fillPrompt('Give me a detailed analysis of the current sensor readings including risk level, trend, and anomaly detection')">AI Sensor Analysis</button>
                    <button class="prompt-chip" onclick="fillPrompt('Generate a threat briefing based on the latest sensor data')">Threat Briefing</button>
                </div>
            </div>
        `;
    } else {
        chatBox.innerHTML = "";

        currentChat.messages.forEach(message => {
            addMessageToUI(message.role, message.text, false);
        });

        chatBox.scrollTop = chatBox.scrollHeight;
    }
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

function typeText(element, text, speed = 12, callback) {
    if (typingTimer) {
        clearInterval(typingTimer);
        typingTimer = null;
    }

    let i = 0;
    element.textContent = "";

    typingTimer = setInterval(() => {
        element.textContent += text.charAt(i);
        i += 1;

        // keep auto-scroll
        chatBox.scrollTop = chatBox.scrollHeight;

        if (i >= text.length) {
            clearInterval(typingTimer);
            typingTimer = null;

            // 👇 THIS is the key addition
            if (callback) callback();
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

const welcome = document.querySelector(".welcome-card");
if (welcome) {
    welcome.remove();
}

renderHistory();
renderCurrentChat();
questionInput.value = "";
startThinking();

    try {
        const response = await fetch("https://chatbot.sisiwenyewe.com/chat", {
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

typeText(bubble, botText, 12, () => {
    if (data.resources && data.resources.length > 0) {
        const resourceDiv = document.createElement("div");
        resourceDiv.className = "resource-links";

        const title = document.createElement("div");
        title.innerText = "For further reading, consult the following authoritative sources:";
        title.className = "resource-title";

        resourceDiv.appendChild(title);

        data.resources.forEach(link => {
            const card = document.createElement("div");
            card.className = "resource-card";

            const a = document.createElement("a");
            a.href = link.url;
            a.target = "_blank";
            a.innerText = link.title;

            card.appendChild(a);
            resourceDiv.appendChild(card);
        });

        bubble.appendChild(resourceDiv);
    }
});

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


const speakBtn = document.getElementById("speak-btn");

let recognition = null;
let isListening = false;
let finalTranscript = "";

function initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
        console.log("Speech recognition not supported in this browser.");
        return null;
    }

    const sr = new SpeechRecognition();

    sr.lang = "en-US";
    sr.interimResults = true;
    sr.continuous = true;
    sr.maxAlternatives = 1;

    // ✅ START
    sr.onstart = () => {
        console.log("Speech recognition started");
    
        // 🔥 TEST MICROPHONE ACCESS
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(() => console.log("✅ Mic permission OK"))
            .catch(err => console.log("❌ Mic permission error:", err));
    
        finalTranscript = "";
        isListening = true;
        updateSpeakButton();
    };

  // ✅ RESULT (live typing + debug)
sr.onresult = (event) => {
    console.log("🎤 Speech result received");

    let interimTranscript = "";

    for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcriptPiece = event.results[i][0].transcript;
        console.log("Piece:", transcriptPiece);

        if (event.results[i].isFinal) {
            finalTranscript += transcriptPiece + " ";
        } else {
            interimTranscript += transcriptPiece;
        }
    }

    const fullText = (finalTranscript + interimTranscript).trim();
    console.log("Full transcript:", fullText);

    questionInput.value = fullText;
    questionInput.focus();
};


// ✅ ERROR HANDLING (improved)
sr.onerror = (event) => {
    console.log("❌ Speech error:", event.error);

    if (event.error === "not-allowed") {
        alert("Microphone permission blocked. Allow mic access.");
        isListening = false;
    } 
    else if (event.error === "audio-capture") {
        alert("No microphone detected.");
        isListening = false;
    } 
    else if (event.error === "no-speech") {
        console.log("⚠️ No speech detected — still listening...");
        return;
    }
    else if (event.error === "network") {
        alert("Speech recognition service is currently unavailable. Please type your question instead.");
        isListening = false;
    }

    updateSpeakButton();
};

    // ✅ CRITICAL FIX: KEEP LISTENING
    sr.onend = () => {
        console.log("Speech recognition ended");

        if (!isListening) {
            updateSpeakButton();
            return;
        }

        // 🔥 auto-restart to prevent instant stop
        try {
            sr.start();
        } catch (e) {
            console.log("Restart error:", e);
            isListening = false;
            updateSpeakButton();
        }
    };

    return sr;
}

function toggleSpeechInput() {
    if (!recognition) {
        recognition = initSpeechRecognition();
    }

    if (!recognition) {
        alert("Speech input is not supported in this browser.");
        return;
    }

    if (isListening) {
        // ✅ manual stop
        isListening = false;
        recognition.stop();
    } else {
        questionInput.focus();

        // 🔥 small delay prevents browser glitch
        setTimeout(() => {
            try {
                recognition.start();
            } catch (e) {
                console.log("Start error:", e);
            }
        }, 200);
    }
}

function updateSpeakButton() {
    if (!speakBtn) return;

    speakBtn.textContent = isListening ? "Listening..." : "Speak";
    speakBtn.classList.toggle("listening", isListening);
}

// ✅ attach listener
if (speakBtn) {
    speakBtn.addEventListener("click", toggleSpeechInput);
}