const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const messages = document.getElementById("messages");
const exampleChips = document.querySelectorAll(".example-chip");
const resetButton = document.getElementById("reset-btn");
const sendBtn = document.getElementById("send-btn");
const navLinks = document.querySelectorAll('a[href^="#"]');

let conversation = null;
let typingNode = null;

/* Smooth scroll for in-page links */
navLinks.forEach((link) => {
    link.addEventListener("click", (e) => {
        const targetId = link.getAttribute("href");
        if (targetId.startsWith("#")) {
            e.preventDefault();
            document.querySelector(targetId)?.scrollIntoView({ behavior: "smooth", block: "start" });
        }
    });
});

/* Entrance animations */
const observer = new IntersectionObserver(
    (entries) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                entry.target.classList.add("visible");
                observer.unobserve(entry.target);
            }
        });
    },
    { threshold: 0.1, rootMargin: "0px 0px -40px 0px" }
);
document.querySelectorAll(".fade").forEach((el) => observer.observe(el));

function appendMessage(role, text) {
    const wrapper = document.createElement("article");
    wrapper.className = `message ${role}`;

    if (role === "assistant") {
        const label = document.createElement("div");
        label.className = "message-label";
        label.textContent = "Assistant";
        wrapper.appendChild(label);

        const body = document.createElement("pre");
        body.className = "message-body";
        body.textContent = text;
        wrapper.appendChild(body);
    } else {
        wrapper.textContent = text;
    }

    messages.appendChild(wrapper);
    messages.scrollTop = messages.scrollHeight;
}

function addTyping() {
    removeTyping();
    const wrap = document.createElement("article");
    wrap.className = "message assistant typing";

    const label = document.createElement("div");
    label.className = "message-label";
    label.textContent = "Assistant";
    wrap.appendChild(label);

    const dots = document.createElement("div");
    dots.style.display = "flex";
    dots.style.gap = "4px";
    ["", "", ""].forEach(() => {
        const d = document.createElement("span");
        d.className = "typing-dot";
        dots.appendChild(d);
    });
    wrap.appendChild(dots);

    messages.appendChild(wrap);
    messages.scrollTop = messages.scrollHeight;
    typingNode = wrap;
}

function removeTyping() {
    if (typingNode && typingNode.parentNode) {
        typingNode.parentNode.removeChild(typingNode);
    }
    typingNode = null;
}

async function sendMessage(message) {
    appendMessage("user", message);
    addTyping();
    input.value = "";
    input.style.height = "auto";
    sendBtn.disabled = true;
    sendBtn.textContent = "Sending…";

    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message, conversation }),
        });

        if (!response.ok) throw new Error("Backend error");

        const payload = await response.json();
        conversation = payload.conversation;
        removeTyping();
        appendMessage("assistant", payload.reply_markdown);
    } catch (error) {
        removeTyping();
        appendMessage(
            "assistant",
            "The system encountered an error. Please confirm the Flask backend is running on port 5000."
        );
    } finally {
        sendBtn.disabled = false;
        sendBtn.textContent = "Send";
    }
}

// Form submission
if (form && input) {
    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const message = input.value.trim();
        if (!message) return;

        input.disabled = true;
        try {
            await sendMessage(message);
        } finally {
            input.disabled = false;
            input.focus();
        }
    });

    // Auto-expanding textarea
    input.addEventListener("input", function() {
        this.style.height = "auto";
        this.style.height = (this.scrollHeight) + "px";
    });
}

exampleChips.forEach((chip) => {
    chip.addEventListener("click", () => {
        if (!input) return;
        input.value = chip.dataset.prompt ?? "";
        input.style.height = "auto";
        input.style.height = (input.scrollHeight) + "px";
        input.focus();
    });
});

if (resetButton) {
    resetButton.addEventListener("click", () => {
        conversation = null;
        if (messages) messages.innerHTML = "";
        appendMessage("assistant", "Experience reset. How can I help you today?");
    });
}
