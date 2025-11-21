document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('debate-form');
    const topicInput = document.getElementById('topic-input');
    const startBtn = document.getElementById('start-btn');
    const stopBtn = document.getElementById('stop-btn');
    const chatContainer = document.getElementById('chat-container');
    const loader = document.getElementById('loader');
    const btnText = startBtn.querySelector('.btn-text');
    const modelSelect = document.getElementById('model-select');
    const settingsBtn = document.getElementById('settings-btn');
    const settingsModal = document.getElementById('settings-modal');
    const closeSettingsBtn = document.getElementById('close-settings');
    const saveSettingsBtn = document.getElementById('save-settings');
    const googleApiKeyInput = document.getElementById('google-api-key');

    let eventSource = null;

    // Load API Key from local storage
    const savedApiKey = localStorage.getItem('google_api_key');
    if (savedApiKey) {
        googleApiKeyInput.value = savedApiKey;
    }

    // Reading Mode Toggle
    const toggleUIBtn = document.getElementById('toggle-ui-btn');
    toggleUIBtn.addEventListener('click', () => {
        document.body.classList.toggle('reading-mode');
        toggleUIBtn.classList.toggle('collapsed');
    });

    // Settings Modal Logic
    settingsBtn.addEventListener('click', () => {
        settingsModal.classList.remove('hidden');
    });

    closeSettingsBtn.addEventListener('click', () => {
        settingsModal.classList.add('hidden');
    });

    saveSettingsBtn.addEventListener('click', () => {
        const apiKey = googleApiKeyInput.value.trim();
        if (apiKey) {
            localStorage.setItem('google_api_key', apiKey);
            alert('Settings saved!');
            settingsModal.classList.add('hidden');
        } else {
            localStorage.removeItem('google_api_key');
            alert('API Key removed.');
            settingsModal.classList.add('hidden');
        }
    });

    // Close modal when clicking outside
    settingsModal.addEventListener('click', (e) => {
        if (e.target === settingsModal) {
            settingsModal.classList.add('hidden');
        }
    });

    const saveBtn = document.getElementById('save-btn');
    const loadBtn = document.getElementById('load-btn');
    const fileInput = document.getElementById('file-input');

    // Save Debate Logic
    saveBtn.addEventListener('click', () => {
        const messages = Array.from(chatContainer.children);
        if (messages.length === 0 || (messages.length === 1 && messages[0].classList.contains('welcome-message'))) {
            alert('저장할 대화 내용이 없습니다.');
            return;
        }

        let markdownContent = `# Debate Topic: ${topicInput.value || 'Untitled'}\n\n`;

        messages.forEach(msgDiv => {
            if (msgDiv.classList.contains('message')) {
                const role = msgDiv.querySelector('.message-role').textContent;
                const content = msgDiv.querySelector('.message-content').innerText; // innerText preserves newlines
                markdownContent += `**${role}**: ${content}\n\n`;
            }
        });

        const blob = new Blob([markdownContent], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        a.download = `debate_${timestamp}.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    });

    // Load Debate Logic
    loadBtn.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (event) => {
            const content = event.target.result;
            parseAndLoadDebate(content);
        };
        reader.readAsText(file);
        fileInput.value = ''; // Reset input
    });

    function parseAndLoadDebate(markdown) {
        chatContainer.innerHTML = ''; // Clear existing chat

        const lines = markdown.split('\n');
        let currentRole = null;
        let currentContent = [];

        // Extract topic
        const topicMatch = markdown.match(/# Debate Topic: (.*)/);
        if (topicMatch) {
            topicInput.value = topicMatch[1].trim();
        }

        // Regex to identify role lines: "**Role**: "
        const roleRegex = /^\*\*(.*)\*\*: (.*)/;

        lines.forEach(line => {
            const match = line.match(roleRegex);
            if (match) {
                // If we have a previous message accumulating, append it
                if (currentRole) {
                    appendMessage(currentRole, currentContent.join('\n').trim());
                }

                // Start new message
                currentRole = mapRoleToInternal(match[1]);
                currentContent = [match[2]];
            } else if (currentRole) {
                // Append to current message content
                currentContent.push(line);
            }
        });

        // Append the last message
        if (currentRole) {
            appendMessage(currentRole, currentContent.join('\n').trim());
        }
    }

    function mapRoleToInternal(displayRole) {
        if (displayRole === '사회자' || displayRole === 'Moderator') return 'moderator';
        if (displayRole === '찬성' || displayRole === 'Proponent') return 'proponent';
        if (displayRole === '반대' || displayRole === 'Opponent') return 'opponent';
        return 'unknown';
    }

    // Helper to append message directly (reused from SSE logic but simplified)
    function appendMessage(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;

        const roleDiv = document.createElement('div');
        roleDiv.className = 'message-role';
        roleDiv.textContent = getDisplayRole(role);

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        // Simple markdown-like parsing for bold text
        let formattedContent = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        formattedContent = formattedContent.replace(/\n/g, '<br>');
        contentDiv.innerHTML = formattedContent;

        messageDiv.appendChild(roleDiv);
        messageDiv.appendChild(contentDiv);
        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function getDisplayRole(role) {
        if (role === 'moderator') return '사회자';
        if (role === 'proponent') return '찬성';
        if (role === 'opponent') return '반대';
        return role;
    }

    // Fetch available models
    fetchModels();

    async function fetchModels() {
        try {
            const response = await fetch('/models');
            const data = await response.json();

            modelSelect.innerHTML = '<option value="" disabled selected>Select Model</option>';

            data.models.forEach(model => {
                const option = document.createElement('option');
                option.value = JSON.stringify({ name: model.name, provider: model.provider });
                option.textContent = `${model.name} (${model.provider})`;
                modelSelect.appendChild(option);
            });

            // Select gemini-2.5-flash by default if available, otherwise first model
            if (data.models.length > 0) {
                const preferredModel = data.models.find(m => m.name === 'gemini-2.5-flash' && m.provider === 'google');
                const defaultModel = preferredModel || data.models[0];
                modelSelect.value = JSON.stringify({ name: defaultModel.name, provider: defaultModel.provider });
            }
        } catch (error) {
            console.error('Error fetching models:', error);
            addSystemMessage("모델 목록을 불러오는데 실패했습니다.");
        }
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const topic = topicInput.value.trim();
        const modelData = modelSelect.value ? JSON.parse(modelSelect.value) : null;

        if (!topic || !modelData) {
            if (!modelData) alert("모델을 선택해주세요.");
            return;
        }

        let apiKey = null;
        if (modelData.provider === 'google') {
            apiKey = localStorage.getItem('google_api_key');
            if (!apiKey) {
                alert("Google API Key가 설정되지 않았습니다. 설정 메뉴에서 키를 입력해주세요.");
                settingsModal.classList.remove('hidden');
                return;
            }
        }

        startDebate(topic, modelData.name, modelData.provider, apiKey);
    });

    stopBtn.addEventListener('click', () => {
        stopDebate();
    });

    // Manual Control UI Elements
    const autoPlayCheckbox = document.getElementById('auto-play');
    const nextBtn = document.getElementById('next-btn');

    // Manual Control State
    let isAutoPlay = true;
    let isWaitingForNext = false;
    let eventQueue = [];
    let isProcessingQueue = false;

    // Streaming state
    let currentRole = null;
    let currentMessageDiv = null;
    let currentContentBuffer = "";
    let currentSessionId = null;

    async function startDebate(topic, model, provider, apiKey) {
        // Reset UI and streaming state
        chatContainer.innerHTML = '';
        currentRole = null;
        currentMessageDiv = null;
        currentContentBuffer = "";
        eventQueue = [];
        isWaitingForNext = false;
        isProcessingQueue = false;
        currentSessionId = null;

        setLoading(true);
        stopBtn.classList.remove('hidden');

        // Reset controls
        isAutoPlay = autoPlayCheckbox.checked;
        nextBtn.disabled = true;

        // Close existing connection if any
        if (eventSource) {
            eventSource.close();
            eventSource = null;
        }

        try {
            // 1. Start Debate Session
            const response = await fetch('/start_debate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    topic,
                    model,
                    provider,
                    google_api_key: apiKey
                })
            });

            if (!response.ok) throw new Error('Failed to start debate');
            const data = await response.json();
            currentSessionId = data.session_id;

            // 2. Start First Turn
            streamTurn();

        } catch (error) {
            console.error('Error starting debate:', error);
            setLoading(false);
            stopBtn.classList.add('hidden');
            addSystemMessage(`오류 발생: ${error.message}`);
        }
    }

    function streamTurn() {
        if (!currentSessionId) {
            console.error("No session ID, cannot stream turn.");
            return;
        }

        console.log("Streaming turn for session:", currentSessionId);

        // Show thinking immediately
        showThinking();

        // Disable next button while streaming
        nextBtn.disabled = true;

        // Connect to SSE endpoint for next turn
        const url = `/next_turn?session_id=${currentSessionId}`;
        console.log("Connecting to SSE:", url);
        eventSource = new EventSource(url);

        eventSource.onopen = () => {
            console.log("SSE connection opened.");
        };

        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            eventQueue.push(data);
            processQueue();
        };

        eventSource.onerror = (error) => {
            console.error('EventSource failed:', error);
            // Check if readyState is CLOSED
            if (eventSource.readyState === EventSource.CLOSED) {
                console.log("SSE connection closed.");
            } else {
                console.log("SSE connection error.");
                // Only show error if we are not in a normal close state (which usually comes from stream_end)
                // But stream_end closes it manually.
                // If we get here, it's likely a network error or server error.
                hideThinking();
                addSystemMessage("서버 연결이 끊어졌습니다. (Connection Error)");
                setLoading(false);
                stopBtn.classList.add('hidden');
            }

            if (eventSource) {
                eventSource.close();
                eventSource = null;
            }
        };
    }

    async function processQueue() {
        if (isProcessingQueue) return;
        // Don't return if isWaitingForNext is true, just don't process. 
        if (isWaitingForNext) return;

        isProcessingQueue = true;

        try {
            while (eventQueue.length > 0) {
                if (isWaitingForNext) break;

                const data = eventQueue.shift();

                if (data.type === 'token') {
                    hideThinking();
                    handleToken(data.role, data.content);
                } else if (data.type === 'turn_end') {
                    // Turn ended logic handled at stream_end usually, 
                    // but we can use this to know a role finished.
                    console.log('Turn end for role:', data.role);
                } else if (data.type === 'stream_end') {
                    // The stream for this turn is done.
                    if (eventSource) {
                        eventSource.close();
                        eventSource = null;
                    }

                    if (!isAutoPlay) {
                        isWaitingForNext = true;
                        nextBtn.disabled = false;
                        chatContainer.scrollTop = chatContainer.scrollHeight;
                    } else {
                        // Auto play: trigger next turn immediately
                        // Small delay for better UX
                        setTimeout(() => streamTurn(), 500);
                    }

                } else if (data.type === 'end') {
                    if (eventSource) {
                        eventSource.close();
                        eventSource = null;
                    }
                    setLoading(false);
                    stopBtn.classList.add('hidden');
                    hideThinking();
                    addSystemMessage("토론이 종료되었습니다.");
                    currentSessionId = null;
                } else if (data.type === 'error') {
                    if (eventSource) {
                        eventSource.close();
                        eventSource = null;
                    }
                    setLoading(false);
                    stopBtn.classList.add('hidden');
                    hideThinking();
                    addSystemMessage(`오류 발생: ${data.content}`);
                    currentSessionId = null;
                }
            }
        } catch (e) {
            console.error("Error in processQueue:", e);
            addSystemMessage(`Error processing events: ${e.message}`);
        } finally {
            isProcessingQueue = false;
        }
    }

    // Auto Play Toggle Logic
    autoPlayCheckbox.addEventListener('change', (e) => {
        isAutoPlay = e.target.checked;
        if (isAutoPlay) {
            if (isWaitingForNext) {
                isWaitingForNext = false;
                nextBtn.disabled = true;
                // Trigger next turn
                streamTurn();
            }
        } else {
            if (isWaitingForNext) {
                nextBtn.disabled = false;
            }
        }
    });

    nextBtn.addEventListener('click', () => {
        if (isWaitingForNext) {
            isWaitingForNext = false;
            nextBtn.disabled = true;
            streamTurn();
        }
    });

    // Allow Enter key to trigger Next
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !nextBtn.disabled && isWaitingForNext) {
            nextBtn.click();
        }
    });

    function handleToken(role, content) {
        if (role !== currentRole) {
            // New speaker, create new message box
            currentRole = role;
            currentContentBuffer = "";
            currentMessageDiv = createMessageDiv(role);
            chatContainer.appendChild(currentMessageDiv);
        }

        // Append token to buffer and update display
        currentContentBuffer += content;
        const contentDiv = currentMessageDiv.querySelector('.message-content');
        contentDiv.innerHTML = formatContent(currentContentBuffer);

        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function createMessageDiv(role) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;

        const roleDiv = document.createElement('div');
        roleDiv.className = 'message-role';
        roleDiv.textContent = getDisplayRole(role);

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        messageDiv.appendChild(roleDiv);
        messageDiv.appendChild(contentDiv);

        return messageDiv;
    }

    let thinkingDiv = null;

    function showThinking() {
        if (thinkingDiv) return; // Already showing

        thinkingDiv = document.createElement('div');
        thinkingDiv.className = 'message thinking';
        thinkingDiv.innerHTML = `
            <div class="message-content">
                <span class="thinking-dots">Thinking</span>
            </div>
        `;
        chatContainer.appendChild(thinkingDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function hideThinking() {
        if (thinkingDiv) {
            thinkingDiv.remove();
            thinkingDiv = null;
        }
    }

    function stopDebate() {
        if (eventSource) {
            eventSource.close();
            eventSource = null;
        }
        setLoading(false);
        stopBtn.classList.add('hidden');
        hideThinking();
        eventQueue = [];
        isProcessingQueue = false;
        isWaitingForNext = false;
        nextBtn.disabled = true;
        currentSessionId = null;
    }

    function setLoading(isLoading) {
        if (isLoading) {
            startBtn.disabled = true;
            btnText.classList.add('hidden');
            loader.classList.remove('hidden');
        } else {
            startBtn.disabled = false;
            btnText.classList.remove('hidden');
            loader.classList.add('hidden');
        }
    }

    function addSystemMessage(text) {
        const div = document.createElement('div');
        div.className = 'system-message';
        div.textContent = text;
        chatContainer.appendChild(div);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function formatContent(text) {
        // Basic formatting for markdown-like features
        // This is a simple implementation. For full markdown support, a library like marked.js would be better.
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // Bold
            .replace(/\n/g, '<br>'); // Newlines
    }
});
