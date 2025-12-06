// frontend/embed.js - Enhanced Embed Script for Websites
(function() {
    'use strict';
    
    // Configuration
    const config = {
        baseUrl: 'http://localhost:5000',
        widgetClosedHeight: 60,
        widgetClosedWidth: 60,
        widgetOpenHeight: 500,
        widgetOpenWidth: 380,
        position: 'bottom-right',
        bottom: 20,
        right: 20,
        zIndex: 10000
    };
    
    // Check if widget is already loaded
    if (window.CredGenWidget && window.CredGenWidget.isLoaded) {
        console.warn('CredGen Widget is already loaded on this page');
        return;
    }
    
    // Create iframe for the widget
    const iframe = document.createElement('iframe');
    iframe.id = 'credgen-chat-widget';
    iframe.src = `${config.baseUrl}/widget.html`;
    iframe.title = 'CredGen Chat Assistant';
    iframe.allow = 'microphone; camera';
    
    // Apply initial closed state styles
    iframe.style.cssText = `
        position: fixed;
        ${config.position === 'bottom-right' ? 
            `bottom: ${config.bottom}px; 
             right: ${config.right}px;` : 
            `bottom: ${config.bottom}px; 
             left: ${config.right}px;`
        }
        width: ${config.widgetClosedWidth}px;
        height: ${config.widgetClosedHeight}px;
        border: none;
        z-index: ${config.zIndex};
        border-radius: 30px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        overflow: hidden;
        background: transparent;
        opacity: 0;
        transform: scale(0.9);
    `;
    
    // Add to page
    document.body.appendChild(iframe);
    
    // Apply initial animation after a short delay
    setTimeout(() => {
        iframe.style.opacity = '1';
        iframe.style.transform = 'scale(1)';
    }, 100);
    
    // State management
    let isOpen = false;
    let sessionId = null;
    
    // Listen for messages from iframe
    window.addEventListener('message', function(event) {
        // Security check - verify origin
        if (event.origin !== config.baseUrl) return;
        
        const data = event.data;
        
        switch (data.type) {
            case 'CREDGEN_RESIZE':
                // Resize iframe
                if (data.height && data.width) {
                    iframe.style.height = data.height + 'px';
                    iframe.style.width = data.width + 'px';
                    iframe.style.borderRadius = data.borderRadius || '16px';
                    isOpen = data.isOpen || false;
                }
                break;
                
            case 'SAVE_SESSION_ID':
                // Store session ID for persistence
                if (data.session_id) {
                    sessionId = data.session_id;
                    localStorage.setItem('CREDGEN_SESSION_ID', sessionId);
                }
                break;
                
            case 'REQUEST_SESSION':
                // Send stored session ID to iframe
                const storedSessionId = localStorage.getItem('CREDGEN_SESSION_ID') || 
                                      'embed-' + Math.random().toString(36).slice(2) + Date.now().toString(36);
                iframe.contentWindow.postMessage({
                    type: 'SESSION_ID',
                    session_id: storedSessionId
                }, config.baseUrl);
                break;
                
            case 'TOGGLE_WIDGET':
                // Toggle widget open/close
                toggleWidget();
                break;
                
            case 'WIDGET_READY':
                // Widget is ready, send initial session
                iframe.contentWindow.postMessage({
                    type: 'SESSION_ID',
                    session_id: localStorage.getItem('CREDGEN_SESSION_ID') || 
                               'embed-' + Math.random().toString(36).slice(2) + Date.now().toString(36)
                }, config.baseUrl);
                break;
        }
    });
    
    // Open widget
    function openWidget() {
        iframe.style.height = config.widgetOpenHeight + 'px';
        iframe.style.width = config.widgetOpenWidth + 'px';
        iframe.style.borderRadius = '16px';
        isOpen = true;
        
        // Notify iframe
        iframe.contentWindow.postMessage({
            type: 'WIDGET_STATE',
            isOpen: true
        }, config.baseUrl);
    }
    
    // Close widget
    function closeWidget() {
        iframe.style.height = config.widgetClosedHeight + 'px';
        iframe.style.width = config.widgetClosedWidth + 'px';
        iframe.style.borderRadius = '30px';
        isOpen = false;
        
        // Notify iframe
        iframe.contentWindow.postMessage({
            type: 'WIDGET_STATE',
            isOpen: false
        }, config.baseUrl);
    }
    
    // Toggle widget
    function toggleWidget() {
        if (isOpen) {
            closeWidget();
        } else {
            openWidget();
        }
    }
    
    // Handle click outside to close (optional)
    document.addEventListener('click', function(event) {
        if (isOpen && !iframe.contains(event.target)) {
            // Check if click is outside the iframe
            const iframeRect = iframe.getBoundingClientRect();
            const clickX = event.clientX;
            const clickY = event.clientY;
            
            if (clickX < iframeRect.left || 
                clickX > iframeRect.right || 
                clickY < iframeRect.top || 
                clickY > iframeRect.bottom) {
                closeWidget();
            }
        }
    });
    
    // Handle escape key to close
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape' && isOpen) {
            closeWidget();
        }
        
        // Ctrl+/ or Cmd+/ to toggle (conflict prevention)
        if ((event.ctrlKey || event.metaKey) && event.key === '/' && !event.shiftKey) {
            event.preventDefault();
            toggleWidget();
        }
    });
    
    // Make widget accessible via global object
    window.CredGenWidget = {
        isLoaded: true,
        
        open: function() {
            openWidget();
            return this;
        },
        
        close: function() {
            closeWidget();
            return this;
        },
        
        toggle: function() {
            toggleWidget();
            return this;
        },
        
        // Send message programmatically
        sendMessage: function(message) {
            if (iframe.contentWindow) {
                iframe.contentWindow.postMessage({
                    type: 'SEND_MESSAGE',
                    message: message
                }, config.baseUrl);
                
                // Auto-open if closed
                if (!isOpen) {
                    this.open();
                }
            }
            return this;
        },
        
        // Attach files programmatically (for advanced use)
        attachFiles: function(files) {
            if (iframe.contentWindow) {
                iframe.contentWindow.postMessage({
                    type: 'ATTACH_FILES',
                    files: files
                }, config.baseUrl);
                
                // Auto-open if closed
                if (!isOpen) {
                    this.open();
                }
            }
            return this;
        },
        
        // Set custom configuration
        config: function(options) {
            Object.assign(config, options);
            
            // Update iframe src if baseUrl changed
            if (options.baseUrl) {
                iframe.src = `${config.baseUrl}/widget.html`;
            }
            
            // Update position if changed
            if (options.position) {
                iframe.style.cssText = iframe.style.cssText.replace(
                    /(bottom|left|right|top):[^;]+;/g, 
                    ''
                );
                
                if (config.position === 'bottom-right') {
                    iframe.style.bottom = `${config.bottom}px`;
                    iframe.style.right = `${config.right}px`;
                } else if (config.position === 'bottom-left') {
                    iframe.style.bottom = `${config.bottom}px`;
                    iframe.style.left = `${config.right}px`;
                }
            }
            
            return this;
        },
        
        // Get current state
        getState: function() {
            return {
                isOpen: isOpen,
                sessionId: sessionId,
                config: { ...config }
            };
        },
        
        // Destroy widget
        destroy: function() {
            window.removeEventListener('message', handleMessage);
            document.removeEventListener('click', handleClickOutside);
            document.removeEventListener('keydown', handleEscape);
            
            if (iframe && iframe.parentNode) {
                iframe.parentNode.removeChild(iframe);
            }
            
            window.CredGenWidget = undefined;
            console.log('CredGen Widget destroyed');
        },
        
        // Initialize with session from external source
        setSession: function(sessionData) {
            if (sessionData && sessionData.session_id) {
                sessionId = sessionData.session_id;
                localStorage.setItem('CREDGEN_SESSION_ID', sessionId);
                
                // Send to iframe if open
                if (iframe.contentWindow) {
                    iframe.contentWindow.postMessage({
                        type: 'SESSION_ID',
                        session_id: sessionId
                    }, config.baseUrl);
                }
            }
            return this;
        }
    };
    
    // Helper functions for internal use
    function handleMessage(event) {
        // Already handled above, but kept for reference
    }
    
    function handleClickOutside(event) {
        // Already handled above, but kept for reference
    }
    
    function handleEscape(event) {
        // Already handled above, but kept for reference
    }
    
    // Auto-initialize with animation
    setTimeout(() => {
        console.log('CredGen Widget loaded! Use CredGenWidget.toggle() to open/close.');
        console.log('Available methods: open(), close(), toggle(), sendMessage(), config(), getState(), destroy()');
    }, 500);
    
    // Optional: Add a small launcher button for mobile/accessibility
    function addLauncherButton() {
        const launcher = document.createElement('button');
        launcher.innerHTML = '<i class="fas fa-comment-dots"></i>';
        launcher.style.cssText = `
            position: fixed;
            bottom: ${config.bottom + 70}px;
            ${config.position === 'bottom-right' ? `right: ${config.right}px;` : `left: ${config.right}px;`}
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            color: white;
            cursor: pointer;
            z-index: ${config.zIndex - 1};
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            opacity: 0;
            transform: translateY(10px);
            transition: all 0.3s ease;
        `;
        
        launcher.addEventListener('click', toggleWidget);
        document.body.appendChild(launcher);
        
        // Animate in
        setTimeout(() => {
            launcher.style.opacity = '0.7';
            launcher.style.transform = 'translateY(0)';
        }, 1000);
        
        // Hover effects
        launcher.addEventListener('mouseenter', () => {
            launcher.style.opacity = '1';
            launcher.style.transform = 'translateY(-2px)';
        });
        
        launcher.addEventListener('mouseleave', () => {
            launcher.style.opacity = '0.7';
            launcher.style.transform = 'translateY(0)';
        });
        
        return launcher;
    }
    
    // Add launcher button on mobile devices
    if ('ontouchstart' in window || navigator.maxTouchPoints) {
        setTimeout(addLauncherButton, 1000);
    }
    
})();