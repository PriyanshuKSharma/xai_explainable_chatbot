const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const messages = document.getElementById("messages");
const exampleChips = document.querySelectorAll(".example-chip");
const resetButton = document.getElementById("reset-btn");

let conversation = null;

function appendMessage(role, text) {
    const wrapper = document.createElement("article");
    wrapper.className = `message ${role}`;

    const label = document.createElement("div");
    label.className = "message-label";
    label.textContent = role === "user" ? "You" : "Assistant";

    const body = document.createElement("pre");
    body.className = "message-body";
    body.textContent = text;

    wrapper.appendChild(label);
    wrapper.appendChild(body);
    messages.appendChild(wrapper);
    messages.scrollTop = messages.scrollHeight;
}

async function sendMessage(message) {
    appendMessage("user", message);
    input.value = "";

    const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            message,
            conversation,
        }),
    });

    if (!response.ok) {
        appendMessage("assistant", "Result:\nSomething went wrong while calling the backend.\n\nExplanation:\n- The request did not complete successfully.\n\nInsight:\n- Check whether the FastAPI server is running.\n\nSuggestion:\n- Restart the server and try again.");
        return;
    }

    const payload = await response.json();
    conversation = payload.conversation;
    appendMessage("assistant", payload.reply_markdown);
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = input.value.trim();
    if (!message) {
        return;
    }

    input.disabled = true;
    resetButton.disabled = true;

    try {
        await sendMessage(message);
    } finally {
        input.disabled = false;
        resetButton.disabled = false;
        input.focus();
    }
});

exampleChips.forEach((chip) => {
    chip.addEventListener("click", () => {
        input.value = chip.dataset.prompt ?? "";
        input.focus();
    });
});

resetButton.addEventListener("click", () => {
    conversation = null;
    messages.innerHTML = "";
    appendMessage(
        "assistant",
        "Result:\nConversation reset.\n\nExplanation:\n- Previous context has been cleared.\n- The next message will be treated as a fresh financial query.\n\nInsight:\n- Resetting is useful when you switch from one finance topic to another.\n\nSuggestion:\n- Ask a new question about loans, interest, SIPs, stocks, or bank plans."
    );
});
