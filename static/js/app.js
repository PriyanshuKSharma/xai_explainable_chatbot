const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const messages = document.getElementById("messages");
const resetButton = document.getElementById("reset-btn");
const sendBtn = document.getElementById("send-btn");
const navLinks = document.querySelectorAll('a[href^="#"]');
const suggestions = document.getElementById("suggestions");
const suggestionButtons = document.querySelectorAll("[data-prompt]");

let conversation = null;
let typingNode = null;

function isSafeLinkHref(rawHref) {
    if (!rawHref) return false;
    const trimmed = String(rawHref).trim();
    if (!trimmed) return false;

    try {
        const url = new URL(trimmed, window.location.href);
        return ["http:", "https:", "mailto:", "tel:"].includes(url.protocol);
    } catch {
        return false;
    }
}

function renderInline(parent, text) {
    const source = String(text ?? "");
    const codeRegex = /`([^`]+)`/g;
    let lastIndex = 0;
    let match;

    const appendEmphasisAndLinks = (node, chunk) => {
        const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
        let linkLastIndex = 0;
        let linkMatch;

        const appendStrongEm = (node2, segment) => {
            const boldRegex = /\*\*([^*]+)\*\*/g;
            let boldLastIndex = 0;
            let boldMatch;

            while ((boldMatch = boldRegex.exec(segment)) !== null) {
                const before = segment.slice(boldLastIndex, boldMatch.index);
                if (before) node2.appendChild(document.createTextNode(before));

                const strong = document.createElement("strong");
                strong.textContent = boldMatch[1];
                node2.appendChild(strong);
                boldLastIndex = boldMatch.index + boldMatch[0].length;
            }

            const remaining = segment.slice(boldLastIndex);
            if (remaining) node2.appendChild(document.createTextNode(remaining));
        };

        while ((linkMatch = linkRegex.exec(chunk)) !== null) {
            const before = chunk.slice(linkLastIndex, linkMatch.index);
            if (before) appendStrongEm(node, before);

            const label = linkMatch[1];
            const href = linkMatch[2];

            if (isSafeLinkHref(href)) {
                const a = document.createElement("a");
                a.href = href;
                a.target = "_blank";
                a.rel = "noreferrer noopener";
                a.textContent = label;
                node.appendChild(a);
            } else {
                appendStrongEm(node, linkMatch[0]);
            }

            linkLastIndex = linkMatch.index + linkMatch[0].length;
        }

        const remaining = chunk.slice(linkLastIndex);
        if (remaining) appendStrongEm(node, remaining);
    };

    while ((match = codeRegex.exec(source)) !== null) {
        const before = source.slice(lastIndex, match.index);
        if (before) appendEmphasisAndLinks(parent, before);

        const code = document.createElement("code");
        code.textContent = match[1];
        parent.appendChild(code);

        lastIndex = match.index + match[0].length;
    }

    const remaining = source.slice(lastIndex);
    if (remaining) appendEmphasisAndLinks(parent, remaining);
}

function renderMarkdownToFragment(markdownText) {
    const text = String(markdownText ?? "").replace(/\r\n?/g, "\n").trimEnd();
    const lines = text.split("\n");
    const fragment = document.createDocumentFragment();

    const isFence = (line) => line.trimStart().startsWith("```");
    const headingMatch = (line) => /^(#{1,3})\s+(.+)$/.exec(line.trim());
    const isUL = (line) => /^(\s*[-*])\s+/.test(line);
    const isOL = (line) => /^\s*\d+\.\s+/.test(line);
    const isQuote = (line) => /^\s*>\s+/.test(line);

    let i = 0;
    while (i < lines.length) {
        const line = lines[i];
        const trimmed = line.trim();

        if (!trimmed) {
            i += 1;
            continue;
        }

        if (isFence(line)) {
            const fenceLine = line.trimStart();
            const lang = fenceLine.slice(3).trim() || null;
            i += 1;
            const codeLines = [];
            while (i < lines.length && !isFence(lines[i])) {
                codeLines.push(lines[i]);
                i += 1;
            }
            if (i < lines.length) i += 1; // consume closing fence

            const pre = document.createElement("pre");
            pre.className = "md-pre";
            const code = document.createElement("code");
            code.className = "md-code";
            if (lang) code.dataset.lang = lang;
            code.textContent = codeLines.join("\n");
            pre.appendChild(code);
            fragment.appendChild(pre);
            continue;
        }

        const heading = headingMatch(line);
        if (heading) {
            const level = heading[1].length;
            const tag = level === 1 ? "h3" : level === 2 ? "h4" : "h5";
            const h = document.createElement(tag);
            h.className = "md-heading";
            renderInline(h, heading[2]);
            fragment.appendChild(h);
            i += 1;
            continue;
        }

        if (isQuote(line)) {
            const quoteLines = [];
            while (i < lines.length && isQuote(lines[i])) {
                quoteLines.push(lines[i].replace(/^\s*>\s+/, ""));
                i += 1;
            }
            const blockquote = document.createElement("blockquote");
            blockquote.className = "md-quote";
            const p = document.createElement("p");
            p.className = "md-p";
            quoteLines.forEach((qLine, idx) => {
                if (idx) p.appendChild(document.createElement("br"));
                renderInline(p, qLine);
            });
            blockquote.appendChild(p);
            fragment.appendChild(blockquote);
            continue;
        }

        if (isUL(line) || isOL(line)) {
            const ordered = isOL(line);
            const list = document.createElement(ordered ? "ol" : "ul");
            list.className = "md-list";

            while (i < lines.length) {
                const itemLine = lines[i];
                if (!(ordered ? isOL(itemLine) : isUL(itemLine))) break;

                const content = ordered
                    ? itemLine.replace(/^\s*\d+\.\s+/, "")
                    : itemLine.replace(/^\s*[-*]\s+/, "");
                const li = document.createElement("li");
                li.className = "md-li";
                renderInline(li, content);
                list.appendChild(li);
                i += 1;
            }

            fragment.appendChild(list);
            continue;
        }

        // Paragraph
        const paraLines = [];
        while (i < lines.length) {
            const l = lines[i];
            if (!l.trim()) break;
            if (isFence(l) || headingMatch(l) || isUL(l) || isOL(l) || isQuote(l)) break;
            paraLines.push(l);
            i += 1;
        }

        const p = document.createElement("p");
        p.className = "md-p";
        paraLines.forEach((pLine, idx) => {
            if (idx) p.appendChild(document.createElement("br"));
            renderInline(p, pLine);
        });
        fragment.appendChild(p);
    }

    return fragment;
}

function setComposerEnabled(enabled) {
    if (input) input.disabled = !enabled;
    if (sendBtn) sendBtn.disabled = !enabled || !input?.value?.trim();
}

function ensureScrollToBottom() {
    const scroll = document.querySelector(".chatgpt-scroll");
    if (!scroll) return;
    scroll.scrollTop = scroll.scrollHeight;
}

function hideSuggestions() {
    if (suggestions) suggestions.style.display = "none";
}

function showSuggestions() {
    if (suggestions) suggestions.style.display = "";
}

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
    const wrapper = document.createElement("div");
    wrapper.className = `chatgpt-message ${role} fade`;

    const avatar = document.createElement("div");
    avatar.className = "chatgpt-avatar";
    avatar.textContent = role === "assistant" ? "A" : "U";
    avatar.setAttribute("aria-hidden", "true");

    const bubble = document.createElement("div");
    bubble.className = "chatgpt-bubble";

    const content = document.createElement("div");
    content.className = "chatgpt-content";
    if (role === "assistant") content.appendChild(renderMarkdownToFragment(text));
    else content.textContent = text;

    bubble.appendChild(content);

    wrapper.appendChild(avatar);
    wrapper.appendChild(bubble);

    if (messages) {
        messages.appendChild(wrapper);
        
        // Trigger transition
        requestAnimationFrame(() => {
            wrapper.classList.add("visible");
        });
        ensureScrollToBottom();
    }
}

function addTyping() {
    removeTyping();
    const wrap = document.createElement("div");
    wrap.className = "chatgpt-message assistant typing fade visible";

    const avatar = document.createElement("div");
    avatar.className = "chatgpt-avatar";
    avatar.textContent = "A";
    avatar.setAttribute("aria-hidden", "true");

    const bubble = document.createElement("div");
    bubble.className = "chatgpt-bubble";

    const dots = document.createElement("div");
    dots.className = "chatgpt-typing";
    ["", "", ""].forEach(() => {
        const d = document.createElement("span");
        d.className = "typing-dot";
        dots.appendChild(d);
    });

    bubble.appendChild(dots);
    wrap.appendChild(avatar);
    wrap.appendChild(bubble);

    if (messages) {
        messages.appendChild(wrap);
        ensureScrollToBottom();
    }
    typingNode = wrap;
}

function removeTyping() {
    if (typingNode && typingNode.parentNode) {
        typingNode.parentNode.removeChild(typingNode);
    }
    typingNode = null;
}

async function sendMessage(message) {
    hideSuggestions();
    appendMessage("user", message);
    addTyping();
    input.value = "";
    input.style.height = "auto";
    setComposerEnabled(false);

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
        setComposerEnabled(true);
    }
}

// Form submission
if (form && input) {
    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const message = input.value.trim();
        if (!message) return;

        try {
            await sendMessage(message);
        } finally {
            input.focus();
        }
    });

    // Auto-expanding textarea
    input.addEventListener("input", function() {
        this.style.height = "auto";
        this.style.height = (this.scrollHeight) + "px";
        if (sendBtn) sendBtn.disabled = !this.value.trim() || this.disabled;
    });

    // Enter to send, Shift+Enter for newline
    input.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            form.requestSubmit();
        }
    });
}

suggestionButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
        if (!input) return;
        const prompt = btn.dataset.prompt ?? "";
        if (!prompt) return;
        input.value = prompt;
        input.style.height = "auto";
        input.style.height = (input.scrollHeight) + "px";
        input.focus();
    });
});

if (resetButton) {
    resetButton.addEventListener("click", () => {
        conversation = null;
        if (messages) messages.innerHTML = "";
        showSuggestions();
        appendMessage(
            "assistant",
            "New chat started.\n\nTry a prompt, for example:\n- Loan eligibility with income + credit score\n- Compound interest for 5 years\n- Live stock price for AAPL"
        );
    });
}

// Initial state
setComposerEnabled(true);
ensureScrollToBottom();
