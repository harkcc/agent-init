const input = document.getElementById('chat-input');
const popup = document.getElementById('mention-popup');
const messagesCont = document.getElementById('messages');
let items = [];

// 配置：后端 API 地址
const API_BASE = "";

let activeIndex = 0;
let isPopupVisible = false;
let session_id = "demo_session_" + Math.floor(Math.random() * 10000);

// 初始化：获取可用 Agents
async function fetchAgents() {
    try {
        const response = await fetch(`${API_BASE}/available_agents`);
        const agents = await response.json();
        renderPopup(agents);
    } catch (e) {
        console.error("无法加载 Agent 列表", e);
        // Fallback data
        renderPopup([
            { name: "lingxing_expert", description: "领星 ERP 财务分析专家", icon: "📊" },
            { name: "search_agent", description: "实时联网信息检索专家", "icon": "🔍" },
            { name: "database_agent", description: "MongoDB 数据库操作专家", "icon": "💾" }
        ]);
    }
}

function renderPopup(agents) {
    popup.innerHTML = agents.map(agent => `
        <div class="mention-item" data-agent="${agent.name}">
            <div class="agent-icon">${agent.icon || '🤖'}</div>
            <div class="agent-info">
                <span class="agent-name">${agent.name}</span>
                <span class="agent-desc">${agent.description || '智能助手'}</span>
            </div>
        </div>
    `).join('');

    items = document.querySelectorAll('.mention-item');
    items.forEach((item, idx) => {
        item.addEventListener('click', () => {
            selectAgent(item.dataset.agent);
        });
    });
}

// 核心输入监听
input.addEventListener('input', (e) => {
    const val = e.target.value;
    const cursorPosition = input.selectionStart;
    const lastChar = val[cursorPosition - 1];

    if (lastChar === '@') {
        showPopup();
    } else if (!val.includes('@') || lastChar === ' ') {
        hidePopup();
    }
});

input.addEventListener('keydown', (e) => {
    if (!isPopupVisible) {
        if (e.key === 'Enter' && input.value.trim() !== "") {
            sendMessage(input.value);
            input.value = "";
        }
        return;
    }

    if (e.key === 'ArrowDown') {
        e.preventDefault();
        updateActive(activeIndex + 1);
    } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        updateActive(activeIndex - 1);
    } else if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault();
        selectAgent(items[activeIndex].dataset.agent);
    } else if (e.key === 'Escape') {
        hidePopup();
    }
});

function showPopup() {
    if (items.length === 0) return;
    popup.style.display = 'block';
    isPopupVisible = true;
    updateActive(0);
}

function hidePopup() {
    popup.style.display = 'none';
    isPopupVisible = false;
}

function updateActive(index) {
    if (index < 0) index = items.length - 1;
    if (index >= items.length) index = 0;

    items.forEach(it => it.classList.remove('active'));
    items[index].classList.add('active');
    activeIndex = index;
}

function selectAgent(name) {
    const val = input.value;
    const atIndex = val.lastIndexOf('@');
    input.value = val.substring(0, atIndex) + '@' + name + ' ';
    hidePopup();
    input.focus();
}

async function sendMessage(text) {
    // 1. 显示用户消息
    appendMessage(text, 'user');

    // 2. 显示Loading状态
    const loadingId = appendMessage("Thinking...", 'bot', true);

    try {
        const response = await fetch(`${API_BASE}/chat/run`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: "test_user",
                session_id: session_id,
                input: text
            })
        });

        const data = await response.json();

        // 4. 更新Bot回复
        const botMsgDiv = document.getElementById(loadingId);
        botMsgDiv.innerText = ""; // 清除 loading

        // 这里假设返回的是最终结果
        botMsgDiv.innerText = data.output || "No response received";

    } catch (e) {
        console.error(e);
        const botMsgDiv = document.getElementById(loadingId);
        botMsgDiv.innerText = "Error: " + e.message;
    }
}

function appendMessage(text, sender, isTemp = false) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender}`;

    if (sender === 'user') {
        const highlightedText = text.replace(/(@\w+)/g, '<span class="agent-tag">$1</span>');
        msgDiv.innerHTML = highlightedText;
    } else {
        msgDiv.innerText = text;
    }

    const id = 'msg-' + Date.now();
    msgDiv.id = id;

    messagesCont.appendChild(msgDiv);
    messagesCont.scrollTop = messagesCont.scrollHeight;

    return id;
}

// 启动加载
fetchAgents();
