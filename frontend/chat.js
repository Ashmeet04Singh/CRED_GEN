// ========== CRED_GEN Unified Chat Widget Logic with File Attachment Support ==========
// Works for both standalone page and iframe embed contexts

(function() {
    'use strict';
    
    // Detect context
    const IS_IFRAME = window.self !== window.top;
    const API_BASE = IS_IFRAME ? '' : (window.location.origin || 'http://localhost:5000');
    
    // Session management
    function getOrCreateSession() {
        const key = 'CREDGEN_SESSION_ID';
        let id = localStorage.getItem(key);
        if (!id) {
            id = 'web-' + Math.random().toString(36).slice(2) + Date.now().toString(36);
            localStorage.setItem(key, id);
        }
        return id;
    }
    
    function resetSession() {
        const key = 'CREDGEN_SESSION_ID';
        localStorage.removeItem(key);
        SESSION_ID = getOrCreateSession();
    }
    
    let SESSION_ID = getOrCreateSession();
    
    // Expose reset function globally
    window.resetChatSession = resetSession;
    
    // File attachment functions
    function getAttachedFiles() {
        if (typeof window.getAttachedFiles === 'function') {
            return window.getAttachedFiles();
        }
        return [];
    }
    
    function clearAttachments() {
        if (typeof window.clearAttachments === 'function') {
            window.clearAttachments();
        }
    }
    
    function createFileAttachmentMessage(files, sender = 'user') {
        const fileCount = files.length;
        let totalSize = 0;
        files.forEach(file => totalSize += file.size);
        
        const fileList = files.map(file => {
            const fileType = getFileType(file.type);
            const icon = getFileIcon(fileType);
            const size = formatBytes(file.size);
            
            return `
                <div class="file-list-item">
                    <div class="file-list-icon">${icon}</div>
                    <div class="file-list-name">${file.name}</div>
                    <div class="file-list-size">${size}</div>
                </div>
            `;
        }).join('');
        
        return `
            <div class="file-message-header">
                <i class="fas fa-paperclip"></i>
                <span>${fileCount} file${fileCount > 1 ? 's' : ''} attached (${formatBytes(totalSize)})</span>
            </div>
            <div class="file-list">
                ${fileList}
            </div>
        `;
    }
    
    function getFileType(mimeType) {
        if (window.getFileType) {
            return window.getFileType(mimeType);
        }
        if (mimeType.startsWith('image/')) return 'image';
        if (mimeType === 'application/pdf') return 'pdf';
        if (mimeType.includes('word') || mimeType.includes('document') || mimeType.includes('text')) return 'document';
        if (mimeType.includes('spreadsheet') || mimeType.includes('excel')) return 'spreadsheet';
        return 'file';
    }
    
    function getFileIcon(type) {
        if (window.getFileIcon) {
            return window.getFileIcon(type);
        }
        const icons = {
            'pdf': '<i class="fas fa-file-pdf"></i>',
            'image': '<i class="fas fa-file-image"></i>',
            'document': '<i class="fas fa-file-word"></i>',
            'spreadsheet': '<i class="fas fa-file-excel"></i>',
            'file': '<i class="fas fa-file"></i>'
        };
        return icons[type] || icons.file;
    }
    
    function formatBytes(bytes, decimals = 2) {
        if (window.formatBytes) {
            return window.formatBytes(bytes, decimals);
        }
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }
    
    // UI Detection & Setup
    function detectOrBuildUI() {
        // Check if elements exist (standalone mode)
        const existingChatbox = document.getElementById('credgen-chatbox');
        const existingMessages = document.getElementById('credgen-messages');
        
        if (existingChatbox && existingMessages) {
            // Standalone mode - elements exist
            return {
                mode: 'standalone',
                chatbox: existingChatbox,
                messages: existingMessages,
                form: document.getElementById('credgen-form'),
                input: document.getElementById('credgen-input'),
                close: document.getElementById('credgen-close'),
                toggle: document.getElementById('credgen-toggle'),
                attachments: document.getElementById('credgen-attachments')
            };
        } else {
            // Iframe mode - build UI
            const container = document.getElementById('credgen-chatbox') || document.body;
            const ui = buildUI();
            if (container !== document.body) {
                container.appendChild(ui);
            } else {
                document.body.appendChild(ui);
            }
            
            return {
                mode: 'iframe',
                chatbox: ui,
                messages: ui.querySelector('#cg-msgs'),
                form: ui.querySelector('#cg-form'),
                input: ui.querySelector('#cg-input'),
                close: ui.querySelector('#cg-close'),
                toggle: null,
                attachments: null
            };
        }
    }
    
    function buildUI() {
        const container = document.createElement('div');
        container.style.cssText = 'width:340px;height:480px;background:#fff;border-radius:12px;box-shadow:0 10px 30px rgba(2,6,23,0.2);overflow:hidden;display:flex;flex-direction:column;font-family:Inter,system-ui,-apple-system,"Segoe UI",Roboto,Arial';
        container.innerHTML = `
            <div style="padding:12px;background:linear-gradient(90deg,#4f46e5,#7c3aed);color:white;font-weight:600;">
                CredGen Assistant
                <button id="cg-close" style="float:right;background:transparent;border:none;color:white;font-size:18px;cursor:pointer;">×</button>
            </div>
            <div id="cg-msgs" style="flex:1;overflow:auto;padding:10px;font-size:14px;background:#f7f8fb;"></div>
            <form id="cg-form" style="display:flex;border-top:1px solid #e6e6e9;">
                <input id="cg-input" placeholder="Type your message..." autocomplete="off" style="flex:1;padding:10px;border:0;font-size:14px;" />
                <button type="submit" style="padding:0 14px;border:0;background:#4f46e5;color:white;font-weight:600;cursor:pointer;">Send</button>
            </form>
        `;
        return container;
    }
    
    // Message rendering with file attachment support
    function appendMessage(text, sender = 'bot', files = null) {
        const ui = detectOrBuildUI();
        if (!ui.messages) return;
        
        if (ui.mode === 'standalone') {
            if (files && files.length > 0) {
                // Create file attachment message
                const fileMessage = document.createElement('div');
                fileMessage.className = `file-attachment-message ${sender}`;
                fileMessage.innerHTML = createFileAttachmentMessage(files, sender);
                ui.messages.appendChild(fileMessage);
            }
            
            if (text && text.trim()) {
                // Create text message
                const textMessage = document.createElement('div');
                textMessage.className = sender === 'user' ? 'user-message' : 'bot-message';
                
                // Add message content
                const messageContent = document.createElement('div');
                messageContent.textContent = text;
                textMessage.appendChild(messageContent);
                
                // Add timestamp
                const timestamp = document.createElement('div');
                timestamp.className = 'message-timestamp';
                timestamp.textContent = new Date().toLocaleTimeString([], { 
                    hour: '2-digit', 
                    minute: '2-digit',
                    hour12: true 
                });
                textMessage.appendChild(timestamp);
                
                ui.messages.appendChild(textMessage);
            }
        } else {
            // Iframe mode - use same CSS classes as standalone for consistent styling
            if (files && files.length > 0) {
                // Create file attachment message (uses CSS classes from styles.css)
                const fileMessage = document.createElement('div');
                fileMessage.className = `file-attachment-message ${sender}`;
                fileMessage.innerHTML = createFileAttachmentMessage(files, sender);
                ui.messages.appendChild(fileMessage);
            }
            
            // Handle text message in iframe mode (use same CSS classes as standalone)
            if (text && text.trim()) {
                const textMessage = document.createElement('div');
                textMessage.className = sender === 'user' ? 'user-message' : 'bot-message';
                
                // Add message content
                const messageContent = document.createElement('div');
                messageContent.textContent = text;
                textMessage.appendChild(messageContent);
                
                // Add timestamp
                const timestamp = document.createElement('div');
                timestamp.className = 'message-timestamp';
                timestamp.textContent = new Date().toLocaleTimeString([], { 
                    hour: '2-digit', 
                    minute: '2-digit',
                    hour12: true 
                });
                textMessage.appendChild(timestamp);
                
                ui.messages.appendChild(textMessage);
            }
        }
        ui.messages.scrollTop = ui.messages.scrollHeight;
    }
    
    function escapeHtml(s) {
        return String(s).replace(/[&<>"'`]/g, function(m) {
            return {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#39;',
                '`': '&#96;'
            }[m];
        });
    }
    
    // Set sending state
    function setSending(isSending) {
        const ui = detectOrBuildUI();
        if (!ui.input || !ui.form) return;
        
        const btn = ui.form.querySelector('button[type="submit"]');
        if (isSending) {
            ui.input.disabled = true;
            if (btn) {
                btn.disabled = true;
                btn.textContent = 'Sending…';
                btn.style.opacity = '0.7';
            }
        } else {
            ui.input.disabled = false;
            if (btn) {
                btn.disabled = false;
                btn.textContent = 'Send';
                btn.style.opacity = '1';
            }
        }
    }
    
    // API calls (unified)
    async function apiCall(path, body = {}) {
        const res = await fetch(`${API_BASE}${path}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Session-ID': SESSION_ID
            },
            body: JSON.stringify(body)
        });
        
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
            throw new Error(data.message || data.error || 'Request failed');
        }
        
        // Update session if provided
        if (res.headers.get('X-Session-ID')) {
            const newSessionId = res.headers.get('X-Session-ID');
            SESSION_ID = newSessionId;
            localStorage.setItem('CREDGEN_SESSION_ID', newSessionId);
            if (IS_IFRAME) {
                parent.postMessage({ type: 'SAVE_SESSION_ID', session_id: newSessionId }, '*');
            }
        }
        
        return data;
    }
    
    // File upload API call
    async function uploadFilesWithMessage(text, files) {
        const formData = new FormData();
        formData.append('message', text || '');
        
        files.forEach(file => {
            formData.append('files', file);
        });
        
        const response = await fetch(`${API_BASE}/api/chat`, {
            method: 'POST',
            headers: {
                'X-Session-ID': SESSION_ID
            },
            body: formData
        });
        
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data.message || data.error || 'Upload failed');
        }
        
        // Update session if provided
        if (response.headers.get('X-Session-ID')) {
            const newSessionId = response.headers.get('X-Session-ID');
            SESSION_ID = newSessionId;
            localStorage.setItem('CREDGEN_SESSION_ID', newSessionId);
            if (IS_IFRAME) {
                parent.postMessage({ type: 'SAVE_SESSION_ID', session_id: newSessionId }, '*');
            }
        }
        
        return data;
    }
    
    // Action handler (unified - handles both old and new action names)
    async function handleAction(action) {
        try {
            if (action === 'call_underwriting' || action === 'call_underwriting_api') {
                appendMessage('Running underwriting check...', 'bot');
                const r = await apiCall('/api/underwrite');
                if (r.underwriting_result) {
                    const status = r.underwriting_result.approval_status ? 'approved' : 'rejected';
                    appendMessage(`Underwriting: ${status} — risk ${r.underwriting_result.risk_score}`, 'bot');
                }
                if (r.message) appendMessage(r.message, 'bot');
                if (r.action) await handleAction(r.action);
            } else if (action === 'call_sales' || action === 'call_sales_api') {
                appendMessage('Fetching offer from sales...', 'bot');
                const r = await apiCall('/api/sales');
                if (r.message) appendMessage(r.message, 'bot');
                if (r.action) await handleAction(r.action);
            } else if (action === 'call_documentation' || action === 'call_documentation_api') {
                appendMessage('Generating document...', 'bot');
                const r = await apiCall('/api/generate-document');
                if (r.message) appendMessage(r.message, 'bot');
                if (r.document) {
                    appendMessage('Document generated successfully!', 'bot');
                }
            }
        } catch (err) {
            appendMessage(`Error: ${err.message}`, 'bot');
        }
    }
    
    // Enhanced sendMessage with file attachment support
    async function sendMessage(text, files = []) {
        if (!text.trim() && files.length === 0) {
            return;
        }
        
        // Display file attachments if any
        if (files.length > 0) {
            appendMessage('', 'user', files);
        }
        
        // Display text message if any
        if (text.trim()) {
            appendMessage(text, 'user');
        }
        
        setSending(true);
        
        try {
            let data;
            if (files.length > 0) {
                // Upload files with message
                data = await uploadFilesWithMessage(text, files);
            } else {
                // Regular text message
                data = await apiCall('/api/chat', { message: text });
            }
            
            if (data.message) {
                appendMessage(data.message, 'bot');
            }
            
            // Handle actions
            if (data.action) {
                await handleAction(data.action);
            } else if (data.worker === 'underwriting') {
                // Legacy support
                await handleAction('call_underwriting');
            }
        } catch (err) {
            appendMessage(`Error: ${err.message}`, 'bot');
        } finally {
            setSending(false);
        }
    }
    
    // Open/close chat (standalone mode)
    function openChat() {
        const ui = detectOrBuildUI();
        if (!ui.chatbox) return;
        ui.chatbox.classList.add('credgen-open');
        ui.chatbox.setAttribute('aria-hidden', 'false');
        if (ui.input) ui.input.focus();
    }
    
    function closeChat() {
        const ui = detectOrBuildUI();
        if (!ui.chatbox) return;
        ui.chatbox.classList.remove('credgen-open');
        ui.chatbox.setAttribute('aria-hidden', 'true');
    }
    
    // Initialize
    function init() {
        const ui = detectOrBuildUI();
        if (!ui.messages || !ui.form || !ui.input) {
            console.warn('CredGen: Required elements not found');
            return;
        }
        
        // Form handler
        ui.form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const text = ui.input.value.trim();
            ui.input.value = '';
            
            // Get attached files
            const files = getAttachedFiles();
            
            // Send message with files
            await sendMessage(text, files);
            
            // Clear attachments after sending
            if (files.length > 0) {
                clearAttachments();
            }
        });
        
        // Close handler
        if (ui.close) {
            ui.close.addEventListener('click', () => {
                if (IS_IFRAME) {
                    parent.postMessage({ type: 'TOGGLE_WIDGET' }, '*');
                } else {
                    closeChat();
                }
            });
        }
        
        // Toggle handler (standalone only)
        if (ui.toggle) {
            ui.toggle.addEventListener('click', () => {
                const isOpen = ui.chatbox.classList.contains('credgen-open');
                if (isOpen) {
                    closeChat();
                } else {
                    openChat();
                }
            });
        }
        
        // Enter key to send message (but not when shift+enter for new line)
        if (ui.input) {
            ui.input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    ui.form.dispatchEvent(new Event('submit'));
                }
            });
        }
        
        // Iframe parent communication
        if (IS_IFRAME) {
            parent.postMessage({ type: 'REQUEST_SESSION' }, '*');
            window.addEventListener('message', (ev) => {
                if (ev.data && typeof ev.data.type === 'string') {
                    if (ev.data.type === 'SESSION_ID' && ev.data.session_id) {
                        SESSION_ID = ev.data.session_id;
                        localStorage.setItem('CREDGEN_SESSION_ID', ev.data.session_id);
                    }
                }
            });
        }
        
        // Initial greeting
        setTimeout(() => {
            appendMessage('Hi, I\'m the CRED_GEN assistant. How can I help with your loan today?', 'bot');
        }, 500);
        
        // Listen for clear chat event
        window.addEventListener('credgen:clear-chat', function() {
            // Clear messages
            if (ui.messages) {
                ui.messages.innerHTML = '';
            }
            
            // Reset session
            resetSession();
            
            // Show new greeting after clearing
            setTimeout(() => {
                appendMessage('Hi, I\'m the CRED_GEN assistant. How can I help with your loan today?', 'bot');
            }, 300);
        });
    }
    
    // Run when DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();