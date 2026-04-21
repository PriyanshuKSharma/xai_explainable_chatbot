const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const messages = document.getElementById("messages");
const resetButton = document.getElementById("reset-btn");
const sidebarNewChatButton = document.getElementById("sidebar-new-chat");
const sendBtn = document.getElementById("send-btn");
const navLinks = document.querySelectorAll('a[href^="#"]');
const historyList = document.getElementById("history-list");
const sidebarToggle = document.getElementById("sidebar-toggle");
const sidebarOverlay = document.getElementById("sidebar-overlay");

let typingNode = null;

const STORAGE_KEY = "financial_xai_chat_history_v1";

let sessions = [];
let activeSessionId = null;

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
    syncSendButtonState();
}

function syncSendButtonState() {
    if (!sendBtn || !input) return;
    sendBtn.disabled = Boolean(input.disabled) || !String(input.value ?? "").trim();
}

function ensureScrollToBottom() {
    const scroll = document.querySelector(".chatgpt-scroll");
    if (!scroll) return;
    scroll.scrollTop = scroll.scrollHeight;
}

function safeJsonParse(text, fallback) {
    try {
        return JSON.parse(text);
    } catch {
        return fallback;
    }
}

function loadFromStorage() {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    const parsed = safeJsonParse(raw ?? "", null);
    if (!parsed || typeof parsed !== "object") return { sessions: [], activeSessionId: null };

    const storedSessions = Array.isArray(parsed.sessions) ? parsed.sessions : [];
    const storedActive = typeof parsed.activeSessionId === "string" ? parsed.activeSessionId : null;

    return { sessions: storedSessions, activeSessionId: storedActive };
}

function saveToStorage() {
    try {
        window.localStorage.setItem(
            STORAGE_KEY,
            JSON.stringify({ sessions, activeSessionId })
        );
    } catch {
        // ignore quota / storage errors
    }
}

function uid() {
    return `s_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

function getSessionById(id) {
    return sessions.find((s) => s && s.id === id) || null;
}

function getActiveSession() {
    return activeSessionId ? getSessionById(activeSessionId) : null;
}

function sessionFirstUserText(session) {
    const msgs = Array.isArray(session?.messages) ? session.messages : [];
    const firstUser = msgs.find((m) => m && m.role === "user" && typeof m.text === "string" && m.text.trim());
    return firstUser ? firstUser.text.trim() : "";
}

function deriveSessionTitle(session) {
    const first = sessionFirstUserText(session);
    if (!first) return "New chat";
    const oneLine = first.replace(/\s+/g, " ");
    return oneLine.length > 34 ? `${oneLine.slice(0, 34)}…` : oneLine;
}

function upsertSession(session) {
    const idx = sessions.findIndex((s) => s && s.id === session.id);
    if (idx >= 0) sessions[idx] = session;
    else sessions.unshift(session);
}

function sortSessionsInPlace() {
    sessions.sort((a, b) => {
        const at = typeof a?.updatedAt === "number" ? a.updatedAt : 0;
        const bt = typeof b?.updatedAt === "number" ? b.updatedAt : 0;
        return bt - at;
    });
}

function formatRelativeTime(ts) {
    if (!ts) return "";
    const diff = Date.now() - ts;
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h`;
    const days = Math.floor(hours / 24);
    return `${days}d`;
}

function openSidebar(open) {
    document.body.classList.toggle("sidebar-open", Boolean(open));
}

function renderHistory() {
    if (!historyList) return;
    historyList.innerHTML = "";

    sessions.forEach((s) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "chatgpt-history-item";
        if (s.id === activeSessionId) btn.classList.add("active");
        btn.dataset.sessionId = s.id;

        const title = document.createElement("div");
        title.className = "chatgpt-history-title";
        title.textContent = s.title || deriveSessionTitle(s);

        const meta = document.createElement("div");
        meta.className = "chatgpt-history-meta";
        meta.textContent = formatRelativeTime(s.updatedAt);

        btn.appendChild(title);
        btn.appendChild(meta);
        historyList.appendChild(btn);
    });
}

function setActiveSession(id) {
    activeSessionId = id;
    saveToStorage();
    renderHistory();
}

function makeWelcomeMessage() {
    return {
        role: "assistant",
        text: "Hello! I’m your Financial XAI Assistant.\n\nTry one of these:\n- Loan check (income + credit score)\n- Compound interest for 5 years\n- Live stock price for AAPL",
    };
}

function renderSuggestionsBlock() {
    const wrap = document.createElement("div");
    wrap.className = "chatgpt-suggestions";
    wrap.id = "suggestions";
    wrap.setAttribute("aria-label", "Suggested prompts");

    const mk = (title, sub, prompt) => {
        const b = document.createElement("button");
        b.type = "button";
        b.className = "chatgpt-suggestion";
        b.dataset.prompt = prompt;

        const t = document.createElement("div");
        t.className = "chatgpt-suggestion-title";
        t.textContent = title;

        const s = document.createElement("div");
        s.className = "chatgpt-suggestion-sub";
        s.textContent = sub;

        b.appendChild(t);
        b.appendChild(s);
        return b;
    };

    wrap.appendChild(
        mk(
            "Loan check",
            "Eligibility + factors",
            "My income is 85000, credit score is 742, loan amount is 1200000"
        )
    );
    wrap.appendChild(
        mk(
            "Interest math",
            "SI/CI explanations",
            "Compound interest on 150000 at 10% for 5 years"
        )
    );
    wrap.appendChild(
        mk(
            "Live stock",
            "yfinance snapshot",
            "Show me stock price for AAPL"
        )
    );

    return wrap;
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
        try {
            observer.observe(wrapper);
        } catch {
            // ignore
        }
        
        // Trigger transition
        requestAnimationFrame(() => {
            wrapper.classList.add("visible");
        });
        ensureScrollToBottom();
    }
}

function renderConversationFromSession(session) {
    if (!messages) return;
    messages.innerHTML = "";

    const msgs = Array.isArray(session?.messages) ? session.messages : [];
    if (!msgs.length) {
        const welcome = makeWelcomeMessage();
        appendMessage("assistant", welcome.text);
        const last = messages.lastElementChild;
        const bubble = last?.querySelector?.(".chatgpt-bubble");
        if (bubble) bubble.appendChild(renderSuggestionsBlock());
        return;
    }

    msgs.forEach((m) => {
        if (!m || typeof m.text !== "string") return;
        appendMessage(m.role === "user" ? "user" : "assistant", m.text);
    });
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
    const session = getActiveSession();
    if (!session) return;

    const userMsg = { role: "user", text: message, ts: Date.now() };
    session.messages = Array.isArray(session.messages) ? session.messages : [];
    session.messages.push(userMsg);

    session.updatedAt = Date.now();
    session.title = session.title || deriveSessionTitle(session);
    upsertSession(session);
    sortSessionsInPlace();
    setActiveSession(session.id);
    saveToStorage();

    appendMessage("user", message);
    addTyping();
    input.value = "";
    input.style.height = "auto";
    setComposerEnabled(false);

    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message, conversation: session.conversation ?? null }),
        });

        if (!response.ok) throw new Error("Backend error");

        const payload = await response.json();
        session.conversation = payload.conversation ?? null;
        removeTyping();

        const assistantText = String(payload.reply_markdown ?? "");
        appendMessage("assistant", assistantText);

        const liveSession = getSessionById(activeSessionId);
        if (liveSession) {
            liveSession.messages = Array.isArray(liveSession.messages) ? liveSession.messages : [];
            liveSession.messages.push({ role: "assistant", text: assistantText, ts: Date.now() });
            liveSession.updatedAt = Date.now();
            liveSession.title = deriveSessionTitle(liveSession);
            liveSession.conversation = session.conversation ?? null;
            upsertSession(liveSession);
            sortSessionsInPlace();
            saveToStorage();
            renderHistory();
        }
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
        syncSendButtonState();
    });

    // Enter to send, Shift+Enter for newline
    input.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            form.requestSubmit();
        }
    });
}

document.addEventListener("click", (event) => {
    const target = event.target instanceof Element ? event.target.closest("[data-prompt]") : null;
    if (!target) return;
    if (!input) return;
    const prompt = target.getAttribute("data-prompt") ?? "";
    if (!prompt) return;
    input.value = prompt;
    input.style.height = "auto";
    input.style.height = (input.scrollHeight) + "px";
    syncSendButtonState();
    input.focus();
});

if (historyList) {
    historyList.addEventListener("click", (event) => {
        const target = event.target instanceof Element ? event.target.closest("[data-session-id]") : null;
        if (!target) return;
        const id = target.getAttribute("data-session-id");
        if (!id) return;
        setActiveSession(id);
        const session = getActiveSession();
        renderConversationFromSession(session);
        ensureScrollToBottom();
        openSidebar(false);
    });
}

if (resetButton) {
    resetButton.addEventListener("click", () => {
        startNewChat();
    });
}

function startNewChat() {
    const newSession = {
        id: uid(),
        title: "New chat",
        createdAt: Date.now(),
        updatedAt: Date.now(),
        messages: [],
        conversation: null,
    };
    sessions.unshift(newSession);
    activeSessionId = newSession.id;
    saveToStorage();
    sortSessionsInPlace();
    renderHistory();
    renderConversationFromSession(newSession);
    ensureScrollToBottom();
    openSidebar(false);
}

if (sidebarNewChatButton) {
    sidebarNewChatButton.addEventListener("click", () => {
        startNewChat();
    });
}

if (sidebarToggle) {
    sidebarToggle.addEventListener("click", () => {
        openSidebar(!document.body.classList.contains("sidebar-open"));
    });
}

if (sidebarOverlay) {
    sidebarOverlay.addEventListener("click", () => {
        openSidebar(false);
    });
}

// Initial state
setComposerEnabled(true);
(() => {
    const loaded = loadFromStorage();
    sessions = Array.isArray(loaded.sessions) ? loaded.sessions : [];
    activeSessionId = typeof loaded.activeSessionId === "string" ? loaded.activeSessionId : null;

    // Normalize
    sessions = sessions
        .filter((s) => s && typeof s.id === "string")
        .map((s) => ({
            id: s.id,
            title: typeof s.title === "string" ? s.title : deriveSessionTitle(s),
            createdAt: typeof s.createdAt === "number" ? s.createdAt : Date.now(),
            updatedAt: typeof s.updatedAt === "number" ? s.updatedAt : Date.now(),
            messages: Array.isArray(s.messages) ? s.messages.filter((m) => m && typeof m.text === "string") : [],
            conversation: typeof s.conversation !== "undefined" ? s.conversation : null,
        }));
    sortSessionsInPlace();

    if (!activeSessionId || !getSessionById(activeSessionId)) {
        if (sessions.length) activeSessionId = sessions[0].id;
        else {
            const seed = { id: uid(), title: "New chat", createdAt: Date.now(), updatedAt: Date.now(), messages: [], conversation: null };
            sessions.unshift(seed);
            activeSessionId = seed.id;
        }
    }

    renderHistory();
    setActiveSession(activeSessionId);
    renderConversationFromSession(getActiveSession());
    ensureScrollToBottom();
})();
