let currentWechatId = null;
let currentContactId = null;
let contacts = [];
let messagePollingInterval = null;
let socket = null;

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM加载完成，初始化联系人管理界面');
    
    loadWechatAccounts();
    
    const chatAiReplyToggle = document.getElementById('chatAiReplyToggle');
    if (chatAiReplyToggle) {
        chatAiReplyToggle.addEventListener('change', function() {
            if (!currentContactId) {
                showToast('提示', '请先选择一个联系人');
                this.checked = false;
                return;
            }
            
            const enabled = this.checked;
            const strategyId = document.getElementById('aiStrategy')?.value || null;
            
            saveAiReplySettings(currentContactId, enabled, strategyId);
        });
    }
    
    
    const searchContactBtn = document.getElementById('searchContactBtn');
    if (searchContactBtn) {
        searchContactBtn.addEventListener('click', function() {
            if (currentWechatId) {
                const searchTerm = document.getElementById('searchContactInput').value.trim();
                loadContacts(currentWechatId, searchTerm);
            } else {
                showToast('提示', '请先选择一个微信账号');
            }
        });
    }

    const searchContactInput = document.getElementById('searchContactInput');
    if (searchContactInput) {
        searchContactInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault(); // 防止表单提交
                if (currentWechatId) {
                    const searchTerm = this.value.trim();
                    loadContacts(currentWechatId, searchTerm);
                } else {
                    showToast('提示', '请先选择一个微信账号');
                }
            }
        });

        searchContactInput.addEventListener('input', function() {
            if (this.value.trim() === '' && currentWechatId) {
                loadContacts(currentWechatId, '');
            }
        });
    }
    
    const messageForm = document.getElementById('messageForm');
    if (messageForm) {
        messageForm.addEventListener('submit', function(e) {
            e.preventDefault(); // 阻止表单默认提交行为
            
            if (!currentContactId) {
                showToast('提示', '请先选择一个联系人');
                return;
            }
            
            const messageInput = document.getElementById('messageInput');
            if (messageInput) {
                const content = messageInput.value.trim();
                
                if (content) {
                    sendMessage(currentContactId, content);
                }
            }
        });
    }
    
    const messageInput = document.getElementById('messageInput');
    if (messageInput) {
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault(); // 防止换行
                
                if (!currentContactId) {
                    showToast('提示', '请先选择一个联系人');
                    return;
                }
                
                const content = this.value.trim();
                
                if (content) {
                    sendMessage(currentContactId, content);
                }
            }
        });
    }
    
    const wechatTabLinks = document.querySelectorAll('#wechatTabs .nav-link');
    if (wechatTabLinks.length > 0) {
        wechatTabLinks.forEach(tab => {
            tab.addEventListener('click', function(e) {
                e.preventDefault();
                
                if (!currentWechatId) {
                    showToast('提示', '请先选择一个微信账号');
                    return;
                }
                
                const tabId = this.getAttribute('href').substring(1);
                
                if (tabId === 'friends') {
                    loadContacts(currentWechatId, '', false);
                } else if (tabId === 'groups') {
                    loadContacts(currentWechatId, '', true);
                } else {
                    loadContacts(currentWechatId, '');
                }
            });
        });
    }
    
    let socketEnabled = false;
fetch('/api/websocket_config')
    .then(response => response.json())
    .then(data => {
        socketEnabled = data.enabled || false;
        if (socketEnabled) {
            if (typeof io !== 'undefined') {
                try {
                    initWebSocket();
                } catch (e) {
                    console.error('WebSocket 初始化失败:', e);
                }
            } else {
                console.log('Socket.IO 前端库未加载，WebSocket功能不可用');
            }
        } else {
            console.log('WebSocket功能已禁用');
        }
    })
    .catch(error => {
        console.error('获取WebSocket配置失败', error);
    });
    
    const showContactSettingsBtn = document.getElementById('showContactSettingsBtn');
    if (showContactSettingsBtn) {
        showContactSettingsBtn.addEventListener('click', function() {
            if (!currentContactId) {
                showToast('提示', '请先选择一个联系人');
                return;
            }
            
            const emptyMessageContainer = document.getElementById('emptyMessageContainer');
            const messageContainer = document.getElementById('messageContainer');
            const contactSettingsContainer = document.getElementById('contactSettingsContainer');
            
            if (emptyMessageContainer) {
                emptyMessageContainer.classList.add('d-none');
            }
            
            if (messageContainer) {
                messageContainer.classList.add('d-none');
            }
            
            if (contactSettingsContainer) {
                contactSettingsContainer.classList.remove('d-none');
            }
            
            loadAiStrategies();
            loadKeywords(currentContactId);
            
            const aiReplyEnabled = document.getElementById('aiReplyEnabled');
            const chatAiReplyToggle = document.getElementById('chatAiReplyToggle');
            if (aiReplyEnabled && chatAiReplyToggle) {
                aiReplyEnabled.checked = chatAiReplyToggle.checked;
            }
        });
    }
    
    const backToMessagesBtn = document.getElementById('backToMessagesBtn');
    if (backToMessagesBtn) {
        backToMessagesBtn.addEventListener('click', function() {
            const contactSettingsContainer = document.getElementById('contactSettingsContainer');
            const messageContainer = document.getElementById('messageContainer');
            
            if (contactSettingsContainer) {
                contactSettingsContainer.classList.add('d-none');
            }
            
            if (messageContainer) {
                messageContainer.classList.remove('d-none');
            }
            
            if (currentContactId) {
                loadMessages(currentContactId);
            }
        });
    }
    
    const aiReplyEnabled = document.getElementById('aiReplyEnabled');
    if (aiReplyEnabled) {
        aiReplyEnabled.addEventListener('change', function() {
            const aiStrategyContainer = document.getElementById('aiStrategyContainer');
            if (aiStrategyContainer) {
                aiStrategyContainer.classList.toggle('d-none', !this.checked);
            }
        });
    }
    
    const keywordFilterEnabled = document.getElementById('keywordFilterEnabled');
    if (keywordFilterEnabled) {
        keywordFilterEnabled.addEventListener('change', function() {
            const keywordFilterContainer = document.getElementById('keywordFilterContainer');
            if (keywordFilterContainer) {
                keywordFilterContainer.classList.toggle('d-none', !this.checked);
            }
            
            const addKeywordBtn = document.getElementById('addKeywordBtn');
			onAccountSelected(account.wechat_id);  // ✅ 加入WebSocket房间
            if (addKeywordBtn) {
                addKeywordBtn.style.display = this.checked ? 'block' : 'none';
            }
        });
    }
    

    const aiReplyForm = document.getElementById('aiReplyForm');
    if (aiReplyForm) {
        aiReplyForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            if (!currentContactId) {
                showToast('提示', '请先选择一个联系人');
                return;
            }
            
            const aiReplyEnabled = document.getElementById('aiReplyEnabled').checked;
            const aiStrategy = document.getElementById('aiStrategy').value;
            
            saveAiReplySettings(currentContactId, aiReplyEnabled, aiStrategy);
            
            const chatAiReplyToggle = document.getElementById('chatAiReplyToggle');
            if (chatAiReplyToggle) {
                chatAiReplyToggle.checked = aiReplyEnabled;
            }
        });
    }
    
    const addKeywordBtn = document.getElementById('addKeywordBtn');
    if (addKeywordBtn) {
        addKeywordBtn.addEventListener('click', function() {
            if (!currentContactId) {
                showToast('提示', '请先选择一个联系人');
                return;
            }
            
            document.getElementById('keywordContactId').value = currentContactId;
            document.getElementById('keywordText').value = '';
            document.getElementById('keywordReplacement').value = '';
            
            const addKeywordModal = new bootstrap.Modal(document.getElementById('addKeywordModal'));
            addKeywordModal.show();
        });
    }
    
    const saveKeywordBtn = document.getElementById('saveKeywordBtn');
    if (saveKeywordBtn) {
        saveKeywordBtn.addEventListener('click', function() {
            const contactId = document.getElementById('keywordContactId').value;
            const keyword = document.getElementById('keywordText').value.trim();
            const replacement = document.getElementById('keywordReplacement').value.trim();
            
            if (!keyword) {
                showToast('提示', '关键词不能为空');
                return;
            }
            
            addKeyword(contactId, keyword, replacement);
            
            const addKeywordModal = bootstrap.Modal.getInstance(document.getElementById('addKeywordModal'));
            addKeywordModal.hide();
        });
    }
    
    const updateKeywordBtn = document.getElementById('updateKeywordBtn');
    if (updateKeywordBtn) {
        updateKeywordBtn.addEventListener('click', function() {
            const keywordId = document.getElementById('editKeywordId').value;
            const keyword = document.getElementById('editKeywordText').value.trim();
            const replacement = document.getElementById('editKeywordReplacement').value.trim();
            
            if (!keyword) {
                showToast('提示', '关键词不能为空');
                return;
            }
            
            updateKeyword(keywordId, keyword, replacement);
            
            const editKeywordModal = bootstrap.Modal.getInstance(document.getElementById('editKeywordModal'));
            editKeywordModal.hide();
        });
    }
    
    const confirmDeleteKeywordBtn = document.getElementById('confirmDeleteKeywordBtn');
    if (confirmDeleteKeywordBtn) {
        confirmDeleteKeywordBtn.addEventListener('click', function() {
            const keywordId = document.getElementById('deleteKeywordId').value;
            
            deleteKeyword(keywordId);
            
            const deleteKeywordModal = bootstrap.Modal.getInstance(document.getElementById('deleteKeywordModal'));
            deleteKeywordModal.hide();
        });
    }
	syncAiReplyInputStatus();
});




function loadWechatAccounts() {
    fetch(`/api/wechat_accounts?user_id=${userId}`)
        .then(response => response.json())
        .then(data => {
            console.log("加载微信账号成功:", data);
            
            const accountsContainer = document.getElementById('wechatAccountsList');
            
            if (data.accounts && data.accounts.length > 0) {
                accountsContainer.innerHTML = '';
                
                data.accounts.forEach(account => {
                    const item = document.createElement('a');
                    item.href = '#';
                    item.className = 'list-group-item list-group-item-action wechat-account-item';
                    item.dataset.id = account.wechat_id;
                    
                    const avatarHtml = account.avatar 
                        ? `<img src="${account.avatar}" alt="${account.nickname}" class="rounded-circle" style="width: 40px; height: 40px;">`
                        : `<div class="avatar-placeholder"><i class="bi bi-person-circle"></i></div>`;
                    
                    item.innerHTML = `
                        <div class="d-flex align-items-center">
                            <div class="avatar-container me-3">
                                ${avatarHtml}
                            </div>
                            <div class="flex-grow-1">
                                <h6 class="mb-0">${account.nickname}</h6>
                                <small class="text-muted">${account.wechat_id}</small>
                            </div>
                        </div>
                    `;
                    
                    item.addEventListener('click', function(e) {
                        e.preventDefault();
                        
                        document.querySelectorAll('.wechat-account-item').forEach(el => el.classList.remove('active'));
                        
                        this.classList.add('active');
                        
                        const wechatId = this.dataset.id;
                        currentWechatId = wechatId;
                        
                        updateCurrentAccountInfo(account);
                        
                        const activeTab = document.querySelector('.nav-link.active').getAttribute('href').substring(1);
                        if (activeTab === 'friends') {
                            loadContacts(wechatId, '', false);
                        } else if (activeTab === 'groups') {
                            loadContacts(wechatId, '', true);
                        } else {
                            loadContacts(wechatId, '');
                        }
                    });
                    
                    accountsContainer.appendChild(item);
                });
                
                if (data.accounts.length > 0) {
                    const firstAccount = accountsContainer.querySelector('.wechat-account-item');
                    if (firstAccount) {
                        firstAccount.click();
                    }
                }
            } else {
                accountsContainer.innerHTML = `
                    <div class="text-center py-5 text-muted">
                        <i class="bi bi-wechat" style="font-size: 2rem;"></i>
                        <p class="mt-2">暂无微信账号</p>
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error("加载微信账号失败:", error);
            document.getElementById('wechatAccountsList').innerHTML = `
                <div class="text-center py-5 text-muted">
                    <i class="bi bi-exclamation-triangle" style="font-size: 2rem;"></i>
                    <p class="mt-2">加载微信账号失败</p>
                </div>
            `;
        });
}

function updateCurrentAccountInfo(account) {
    document.getElementById('currentAccountName').textContent = account.nickname;
    document.getElementById('currentAccountId').textContent = account.wechat_id;
    
    const avatarContainer = document.getElementById('currentAccountAvatar');
    if (account.avatar) {
        avatarContainer.innerHTML = `<img src="${account.avatar}" alt="${account.nickname}" class="rounded-circle">`;
    } else {
        avatarContainer.innerHTML = `<div class="avatar-placeholder"><i class="bi bi-person-circle"></i></div>`;
    }
}

function loadContacts(wechatId, searchTerm = '', isGroup = null) {
    let url = `/api/contacts?owner_id=${userId}&wechat_id=${wechatId}`;
    
    if (isGroup !== null) {
        url += `&is_group=${isGroup}`;
    }
    
    if (searchTerm) {
        url += `&search=${encodeURIComponent(searchTerm)}`;
    }
    
    console.log("搜索URL:", url); // 调试日志
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            console.log("加载联系人成功:", data);
            contacts = data.contacts || [];
            renderContacts(contacts, 1, 10);
            
            if (searchTerm) {
                const contactsContainer = document.getElementById('contactsList');
                if (contacts.length === 0) {
                    contactsContainer.innerHTML = `
                        <div class="text-center py-5 text-muted">
                            <i class="bi bi-search" style="font-size: 2rem;"></i>
                            <p class="mt-2">未找到匹配"${searchTerm}"的联系人</p>
                        </div>
                    `;
                } else {
                    const searchInfo = document.createElement('div');
                    searchInfo.className = 'alert alert-info m-2';
                    searchInfo.innerHTML = `找到 ${contacts.length} 个匹配"${searchTerm}"的联系人`;
                    contactsContainer.insertBefore(searchInfo, contactsContainer.firstChild);
                }
            }
        })
        .catch(error => {
            console.error("加载联系人失败:", error);
            showToast('错误', '加载联系人失败');
            
            const contactsContainer = document.getElementById('contactsList');
            contactsContainer.innerHTML = `
                <div class="text-center py-5 text-muted">
                    <i class="bi bi-exclamation-triangle" style="font-size: 2rem;"></i>
                    <p class="mt-2">加载联系人失败</p>
                </div>
            `;
        });
}

function renderContacts(contactsList, page = 1, pageSize = 20) {
		contactsList.sort((a, b) => {
        // 以last_message_time为主，没有就用last_sync_time
        const ta = a.last_message_time || a.last_sync_time || 0;
        const tb = b.last_message_time || b.last_sync_time || 0;
        return new Date(tb) - new Date(ta);
        });
    const contactsContainer = document.getElementById('contactsList');
    if (contactsList.length === 0) {
        contactsContainer.innerHTML = `
            <div class="text-center py-5 text-muted">
                <i class="bi bi-people" style="font-size: 2rem;"></i>
                <p class="mt-2">暂无联系人</p>
            </div>
        `;
        // 清空分页控件
        const oldPagination = document.getElementById('contactsPagination');
        if (oldPagination) oldPagination.remove();
        return;
    }
    contactsContainer.innerHTML = '';
    // 分页逻辑
    const startIdx = (page - 1) * pageSize;
    const endIdx = Math.min(startIdx + pageSize, contactsList.length);
    const pageContacts = contactsList.slice(startIdx, endIdx);
    pageContacts.forEach(contact => {
        const item = document.createElement('a');
        item.href = '#';
        item.className = 'list-group-item list-group-item-action contact-item';
        item.dataset.id = contact.id;
        const showName = contact.remark || contact.nickname || contact.wechat_id;
        const avatarHtml = contact.avatar
            ? `<img src="${contact.avatar}" alt="${showName}" class="rounded-circle" style="width: 40px; height: 40px;">`
            : `<div class="avatar-placeholder"><i class="bi bi-person"></i></div>`;
        const lastMessage = contact.last_message || '';
        const lastMessageTime = contact.last_message_time ? formatTime(contact.last_message_time) : formatTime(contact.last_sync_time);
        const unreadBadge = contact.unread_count > 0 
            ? `<span class="badge bg-danger rounded-pill">${contact.unread_count}</span>` 
            : '';
        item.innerHTML = `
            <div class="d-flex align-items-center">
                <div class="avatar-container me-3">
                    ${avatarHtml}
                </div>
                <div class="flex-grow-1">
                    <div class="d-flex justify-content-between align-items-center">
                        <div class="contact-info d-flex align-items-center">
                            <h6 class="mb-0">${showName}</h6>
                            ${unreadBadge}
                        </div>
                        <small class="text-muted message-time">${lastMessageTime}</small>
                    </div>
                    <div class="d-flex justify-content-between align-items-center">
						<small class="text-muted text-truncate" style="max-width: 70%;">${lastMessage || showName}</small>
                        <span class="badge ${contact.is_group ? 'bg-info' : 'bg-primary'} ms-1">${contact.is_group ? '群聊' : '好友'}</span>
                    </div>
                </div>
            </div>
        `;
		   item.addEventListener('click', function(e) {
            e.preventDefault();
            document.querySelectorAll('.contact-item').forEach(el => el.classList.remove('active'));
            this.classList.add('active');
			currentContactId = contact.wechat_id;
            window.currentContactDbId = contact.id;
			 // 新增👇（加在这里，紧跟currentContactId赋值后面即可）
            if (contact.unread_count && contact.unread_count > 0) {
                 contact.unread_count = 0;
                 renderContacts(contacts, 1, 10);  // 立即刷新UI
             }
            const messageContainer = document.getElementById('messageContainer');
            const contactSettingsContainer = document.getElementById('contactSettingsContainer');
            const emptyMessageContainer = document.getElementById('emptyMessageContainer');
            if (messageContainer) messageContainer.classList.remove('d-none');
            if (contactSettingsContainer) contactSettingsContainer.classList.add('d-none');
            if (emptyMessageContainer) emptyMessageContainer.classList.add('d-none');
            document.getElementById('contactName').textContent = showName;
            document.getElementById('contactWechatId').textContent = contact.wechat_id;
			document.getElementById('contactId').value = contact.wechat_id;
            document.getElementById('aiContactId').value = contact.id;
            // 设置右侧头像
            const avatarContainer = document.getElementById('contactAvatar');
            if (avatarContainer) {
                if (contact.avatar) {
                    avatarContainer.innerHTML = `<img src="${contact.avatar}" alt="头像" style="width:100%;height:100%;">`;
                } else {
                    avatarContainer.innerHTML = `<div class="avatar-placeholder"><i class="bi bi-person"></i></div>`;
                }
            }
            if (contact.unread_count > 0) {
                clearUnreadCount(contact.id);
            }
            loadMessages(contact.id);
            updateContactSettings(contact);
			syncAiReplyInputStatus(); // 保证切换联系人后状态同步
        });
        contactsContainer.appendChild(item);
    });
	
	function renderContactsPagination(total, page, pageSize) {
    let paginationContainer = document.getElementById('contactsPagination');
    if (!paginationContainer) {
        paginationContainer = document.createElement('div');
        paginationContainer.id = 'contactsPagination';
        paginationContainer.className = 'd-flex justify-content-center my-2 flex-wrap';
        document.getElementById('contactsList').after(paginationContainer);
    }

    paginationContainer.innerHTML = '';
    const totalPages = Math.ceil(total / pageSize);
    if (totalPages <= 1) {
        paginationContainer.innerHTML = '';
        return;
    }

    // 上一页
    const prevBtn = document.createElement('button');
    prevBtn.className = 'btn btn-sm btn-outline-primary mx-1 mb-1';
    prevBtn.textContent = '上一页';
    prevBtn.disabled = page === 1;
    prevBtn.onclick = () => renderContacts(contacts, page - 1, pageSize);
    paginationContainer.appendChild(prevBtn);

    // 分页主逻辑
    let pageList = [];
    if (totalPages <= 7) {
        // 全部显示
        for (let i = 1; i <= totalPages; i++) pageList.push(i);
    } else {
        // 总页数多，做折叠
        pageList.push(1);
        if (page > 4) pageList.push('...');
        let start = Math.max(2, page - 2);
        let end = Math.min(totalPages - 1, page + 2);
        for (let i = start; i <= end; i++) pageList.push(i);
        if (page + 2 < totalPages - 1) pageList.push('...');
        pageList.push(totalPages);
    }

    pageList.forEach(p => {
        if (p === '...') {
            const dot = document.createElement('span');
            dot.className = 'btn btn-sm btn-light mx-1 mb-1 disabled';
            dot.textContent = '...';
            paginationContainer.appendChild(dot);
        } else {
            const btn = document.createElement('button');
            btn.className = `btn btn-sm mx-1 mb-1 ${p === page ? 'btn-primary' : 'btn-outline-primary'}`;
            btn.textContent = p;
            btn.disabled = p === page;
            btn.onclick = () => renderContacts(contacts, p, pageSize);
            paginationContainer.appendChild(btn);
        }
    });

    // 下一页
    const nextBtn = document.createElement('button');
    nextBtn.className = 'btn btn-sm btn-outline-primary mx-1 mb-1';
    nextBtn.textContent = '下一页';
    nextBtn.disabled = page === totalPages;
    nextBtn.onclick = () => renderContacts(contacts, page + 1, pageSize);
    paginationContainer.appendChild(nextBtn);
    }
    // 渲染分页控件
    renderContactsPagination(contactsList.length, page, pageSize);
}


function loadMessages(contactId, limit = 50, offset = 0) {
    fetch(`/api/messages?contact_id=${contactId}&limit=${limit}&offset=${offset}`)
        .then(response => response.json())
        .then(data => {
            renderMessages(data.messages || []);
        })
        .catch(error => {
            console.error('加载消息失败:', error);
            document.getElementById('messagesContainer').innerHTML = `
                <div class="text-center py-5 text-muted">
                    <i class="bi bi-exclamation-triangle" style="font-size: 2rem;"></i>
                    <p class="mt-2">加载消息失败</p>
                </div>
            `;
        });
}

function renderMessages(messages) {
    const messagesContainer = document.getElementById('messagesContainer');
    
    if (!messages || messages.length === 0) {
        messagesContainer.innerHTML = `
            <div class="text-center py-5 text-muted">
                <i class="bi bi-chat" style="font-size: 2rem;"></i>
                <p class="mt-2">暂无消息</p>
            </div>
        `;
        return;
    }
    
    messagesContainer.innerHTML = '';
    
    messages.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
    
	messages.forEach(message => {
    console.log('message:', message);

    // 1. 判断消息是否是自己发的
    let isFromMe;
    if (message.send_type) {
        // send_type: 'active' 右侧，'passive' 左侧
        isFromMe = message.send_type === 'active';
    } else {
        // 没有 send_type 字段时降级为 sender_id 逻辑
        isFromMe = (message.sender_id === currentWechatId);
    }

    // 2. 组装消息dom
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isFromMe ? 'message-sent' : 'message-received'}`;

    let messageContent = '';
    if (message.content_type === 'text') {
        messageContent = `<div class="message-text">${message.content}</div>`;
    } else if (message.content_type === 'image') {
        messageContent = `<div class="message-image"><img src="${message.image_url}" alt="图片消息" class="img-fluid rounded"></div>`;
    } else {
        messageContent = `<div class="message-text">[${message.content_type}消息]</div>`;
    }

    messageDiv.innerHTML = `
        <div class="message-content">
            ${messageContent}
            <div class="message-time">${formatTime(message.created_at)}</div>
        </div>
    `;
    messagesContainer.appendChild(messageDiv);
});

    
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}
function getRandomId() {
    return 'msg-' + Math.random().toString(36).slice(2) + Date.now();
}
function sendMessage(contactId, content, contentType = 'text', useWebSocket = false) {
    if (!content || !contactId) return;
    
    if (contentType === 'text') {
        document.getElementById('messageInput').value = '';
    }
    
    const messagesContainer = document.getElementById('messagesContainer');
    //const tempMessageId = 'msg-' + Date.now();
	const tempMessageId = 'msg-' + (crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2) + Date.now());
    const tempMessage = document.createElement('div');
    tempMessage.className = 'message message-sent';
    tempMessage.id = tempMessageId;
	

    
    let messageContent = '';
    if (contentType === 'text') {
        messageContent = `<div class="message-text">${content}</div>`;
    } else if (contentType === 'image') {
        messageContent = `<div class="message-image"><img src="${content}" alt="图片消息" class="img-fluid rounded"></div>`;
    }
    
    tempMessage.innerHTML = `
        <div class="message-content">
            ${messageContent}
            <div class="message-time">
                <span class="sending-indicator">发送中...</span>
            </div>
        </div>
    `;
    
    messagesContainer.appendChild(tempMessage);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    if (useWebSocket && window.globalSocket && window.globalSocket.connected) {
        window.globalSocket.emit('send_direct_message', {
            user_id: userId,
            wechat_id: currentWechatId,
            contact_id: contactId,
            content: content,
            content_type: contentType,
            send_type: 'active'
        });
        
        window.globalSocket.once('message_sent', function(data) {
            if (data.message_id) {
                const tempMsg = document.getElementById(tempMessageId);
                if (tempMsg) {
                    const timeElement = tempMsg.querySelector('.message-time');
                    if (timeElement) {
                        timeElement.innerHTML = formatTime(new Date());
                    }
                }
            } else {
                const tempMsg = document.getElementById(tempMessageId);
                if (tempMsg) {
                    const timeElement = tempMsg.querySelector('.message-time');
                    if (timeElement) {
                        timeElement.innerHTML = `<span class="text-danger">发送失败</span>`;
                    }
                }
                showToast('错误', '发送失败');
            }
        });
        
        window.currentSocket.once('error', function(error) {
            console.error('WebSocket发送消息失败:', error);
            
            const tempMsg = document.getElementById(tempMessageId);
            if (tempMsg) {
                const timeElement = tempMsg.querySelector('.message-time');
                if (timeElement) {
                    timeElement.innerHTML = `<span class="text-danger">发送失败</span>`;
                }
            }
            showToast('错误', error.message || '发送失败');
        });
        
        const chatAiReplyToggle = document.getElementById('chatAiReplyToggle');
        if (chatAiReplyToggle && chatAiReplyToggle.checked) {
            fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_id: currentWechatId,
                    nameuser: document.getElementById('contactName').textContent,
                    content: content,
                    contact_id: contactId
                }),
            })
            .then(response => response.json())
            .then(chatData => {
                if (chatData.reply && chatData.reply.trim() !== '') {
                    const aiMessage = document.createElement('div');
                    aiMessage.className = 'message message-received';
                    aiMessage.innerHTML = `
                        <div class="message-content">
                            <div class="message-text">${chatData.reply}</div>
                            <div class="message-time">${formatTime(new Date())}</div>
                        </div>
                    `;
                    messagesContainer.appendChild(aiMessage);
                    messagesContainer.scrollTop = messagesContainer.scrollHeight;
                }
            })
            .catch(error => {
                console.error('获取AI回复失败:', error);
            });
        }
    } else {
        fetch('/api/send_message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                owner_id: userId, // 使用用户ID而非微信ID
                //contact_ids: [contactId], // 包装为数组以匹配API期望格式
				contact_ids: [window.currentContactDbId], // 数据库ID
                content: content,
                content_type: contentType,
				extra_id: tempMessageId    // 新增，带上临时ID
            }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const tempMsg = document.getElementById(tempMessageId);
                if (tempMsg) {
                    const timeElement = tempMsg.querySelector('.message-time');
                    if (timeElement) {
                        timeElement.innerHTML = formatTime(new Date());
                    }
                }
                

                
                const chatAiReplyToggle = document.getElementById('chatAiReplyToggle');
                if (chatAiReplyToggle && chatAiReplyToggle.checked) {
                    fetch('/api/chat', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            user_id: currentWechatId,
                            nameuser: document.getElementById('contactName').textContent,
                            content: content,
                            contact_id: contactId
                        }),
                    })
                    .then(response => response.json())
                    .then(chatData => {
                        if (chatData.reply && chatData.reply.trim() !== '') {
                            const aiMessage = document.createElement('div');
                            aiMessage.className = 'message message-received';
                            aiMessage.innerHTML = `
                                <div class="message-content">
                                    <div class="message-text">${chatData.reply}</div>
                                    <div class="message-time">${formatTime(new Date())}</div>
                                </div>
                            `;
                            messagesContainer.appendChild(aiMessage);
                            messagesContainer.scrollTop = messagesContainer.scrollHeight;
                        }
                    })
                    .catch(error => {
                        console.error('获取AI回复失败:', error);
                    });
                }
            } else {
                const tempMsg = document.getElementById(tempMessageId);
                if (tempMsg) {
                    const timeElement = tempMsg.querySelector('.message-time');
                    if (timeElement) {
                        timeElement.innerHTML = `<span class="text-danger">发送失败</span>`;
                    }
                }
                showToast('错误', data.error || '发送失败');
            }
        })
        .catch(error => {
            console.error('发送消息失败:', error);
            
            const tempMsg = document.getElementById(tempMessageId);
            if (tempMsg) {
                const timeElement = tempMsg.querySelector('.message-time');
                if (timeElement) {
                    timeElement.innerHTML = `<span class="text-danger">发送失败</span>`;
                }
            }
            showToast('错误', '发送失败');
        });
    }
}

function formatTime(dateString) {
    if (!dateString) return '';
    
    const date = new Date(dateString);
    
    if (isNaN(date.getTime())) {
        return '';
    }
    
    const now = new Date();
    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    const timeStr = `${hours}:${minutes}`;
    
    if (date.toDateString() === now.toDateString()) {
        return timeStr;
    }
    
    if (date.toDateString() === yesterday.toDateString()) {
        return `昨天 ${timeStr}`;
    }
    
    if (date.getFullYear() === now.getFullYear()) {
        const month = (date.getMonth() + 1).toString().padStart(2, '0');
        const day = date.getDate().toString().padStart(2, '0');
        return `${month}-${day} ${timeStr}`;
    }
    
    const year = date.getFullYear();
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const day = date.getDate().toString().padStart(2, '0');
    return `${year}-${month}-${day} ${timeStr}`;
}

function updateContactSettings(contact) {
    const nameInput = document.getElementById('contactDisplayName');
    if (nameInput) nameInput.value = contact.nickname || '';

    const remarkInput = document.getElementById('contactRemark');
    if (remarkInput) remarkInput.value = contact.remark || '';

    const typeInput = document.getElementById('contactType');
    if (typeInput) typeInput.value = contact.is_group ? '群聊' : '好友';

    const aiReplyEnabled = document.getElementById('aiReplyEnabled');
    if (aiReplyEnabled) {
        aiReplyEnabled.checked = contact.ai_reply_enabled || false;
        const aiStrategyContainer = document.getElementById('aiStrategyContainer');
        if (aiStrategyContainer) {
            aiStrategyContainer.classList.toggle('d-none', !aiReplyEnabled.checked);
        }
    }

    const aiStrategy = document.getElementById('aiStrategy');
    if (aiStrategy && contact.ai_strategy_id) {
        aiStrategy.value = contact.ai_strategy_id;
    }
    if (aiStrategy && aiStrategy.options.length <= 1) {
        loadAiStrategies();
    }

    const keywordFilterEnabled = document.getElementById('keywordFilterEnabled');
    if (keywordFilterEnabled) {
        keywordFilterEnabled.checked = contact.keyword_filter_enabled || false;
        const keywordFilterContainer = document.getElementById('keywordFilterContainer');
        if (keywordFilterContainer) {
            keywordFilterContainer.classList.toggle('d-none', !keywordFilterEnabled.checked);
        }
        const addKeywordBtn = document.getElementById('addKeywordBtn');
        if (addKeywordBtn) {
            addKeywordBtn.style.display = keywordFilterEnabled.checked ? 'block' : 'none';
        }
    }

    const chatAiReplyToggle = document.getElementById('chatAiReplyToggle');
    if (chatAiReplyToggle) {
        chatAiReplyToggle.checked = contact.ai_reply_enabled || false;
    }

    syncAiReplyInputStatus();
    loadKeywords(contact.id);
}

function loadAiStrategies() {
    fetch('/api/ai_strategies')
        .then(response => response.json())
        .then(data => {
            const aiStrategy = document.getElementById('aiStrategy');
            if (aiStrategy && data.strategies) {
                const defaultOption = aiStrategy.options[0];
                aiStrategy.innerHTML = '';
                aiStrategy.appendChild(defaultOption);
                
                data.strategies.forEach(strategy => {
                    const option = document.createElement('option');
                    option.value = strategy.id;
                    option.textContent = strategy.name;
                    aiStrategy.appendChild(option);
                });
            }
        })
        .catch(error => {
            console.error('加载AI策略失败:', error);
            showToast('错误', '加载AI策略失败');
        });
}

function loadKeywords(contactId) {
    if (!contactId) return;
    
    fetch(`/api/keywords?contact_id=${contactId}`)
        .then(response => response.json())
        .then(data => {
            const keywordFilterList = document.getElementById('keywordFilterList');
            if (keywordFilterList) {
                keywordFilterList.innerHTML = '';
                
                if (data.keywords && data.keywords.length > 0) {
                    data.keywords.forEach(keyword => {
                        const row = document.createElement('tr');
                        row.innerHTML = `
                            <td>${keyword.keyword}</td>
                            <td>${keyword.replacement || '(删除)'}</td>
                            <td>
                                <button class="btn btn-sm btn-outline-primary edit-keyword" data-id="${keyword.id}">
                                    <i class="bi bi-pencil"></i>
                                </button>
                                <button class="btn btn-sm btn-outline-danger delete-keyword" data-id="${keyword.id}">
                                    <i class="bi bi-trash"></i>
                                </button>
                            </td>
                        `;
                        
                        const editBtn = row.querySelector('.edit-keyword');
                        if (editBtn) {
                            editBtn.addEventListener('click', function() {
                                editKeyword(keyword.id, keyword.keyword, keyword.replacement);
                            });
                        }
                        
                        const deleteBtn = row.querySelector('.delete-keyword');
                        if (deleteBtn) {
                            deleteBtn.addEventListener('click', function() {
                                deleteKeyword(keyword.id);
                            });
                        }
                        
                        keywordFilterList.appendChild(row);
                    });
                } else {
                    const emptyRow = document.createElement('tr');
                    emptyRow.innerHTML = `
                        <td colspan="3" class="text-center">暂无关键词</td>
                    `;
                    keywordFilterList.appendChild(emptyRow);
                }
            }
        })
        .catch(error => {
            console.error('加载关键词失败:', error);
            showToast('错误', '加载关键词失败');
        });
}

// --- 这是修正后的新函数，请用它替换上面的旧函数 ---
function saveAiReplySettings(contactId, enabled, strategyId) {
    if (!contactId) return;

    // 向服务器发送请求的逻辑保持不变，因为您说这部分是正常的
    fetch('/api/set_ai_reply', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            owner_id: currentWechatId,
            contact_id: contactId,
            ai_reply_enabled: enabled,
            ai_strategy_id: strategyId
        }),
    })
    .then(response => {
        // 增加网络和服务器错误判断
        if (!response.ok) {
            // 如果HTTP状态码不是2xx, 抛出错误以便进入.catch块
            throw new Error(`服务器错误: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            showToast('成功', 'AI自动回复设置已保存');

            // [核心修正] 在这里更新前端的“通讯录名单”
            // 使用 c.wechat_id 进行匹配，因为传入的 contactId 是微信ID
            const contactIndex = contacts.findIndex(c => c.wechat_id == contactId);

            if (contactIndex !== -1) {
                // 找到联系人后，更新它的AI开关状态
                contacts[contactIndex].ai_reply_enabled = enabled;
                contacts[contactIndex].ai_strategy_id = strategyId;
                console.log('前端缓存已同步更新:', contacts[contactIndex]);
            } else {
                console.warn('在前端缓存中未找到要更新的联系人:', contactId);
            }

            // 更新UI上其他相关的元素（这部分逻辑保留）
            const aiReplyEnabled = document.getElementById('aiReplyEnabled');
            if (aiReplyEnabled) {
                aiReplyEnabled.checked = enabled;
                const aiStrategyContainer = document.getElementById('aiStrategyContainer');
                if (aiStrategyContainer) {
                    aiStrategyContainer.classList.toggle('d-none', !enabled);
                }
            }
            const chatAiReplyToggle = document.getElementById('chatAiReplyToggle');
            if (chatAiReplyToggle) {
                chatAiReplyToggle.checked = enabled;
            }

        } else {
            // 如果后端返回 success: false, 也抛出错误
            throw new Error(data.error || '保存失败');
        }
    })
    .catch(error => {
        // 统一处理所有错误 (网络或业务逻辑错误)
        console.error('保存AI设置失败:', error);
        showToast('错误', error.message);

        // 发生错误时，将开关恢复到操作前的状态，防止UI显示错误
        const chatAiReplyToggle = document.getElementById('chatAiReplyToggle');
        if (chatAiReplyToggle) {
            chatAiReplyToggle.checked = !enabled;
        }
    });
}
function syncAiReplyInputStatus() {
    const aiToggle = document.getElementById('chatAiReplyToggle');
    const messageInput = document.getElementById('messageInput');
    const sendBtn = document.querySelector('#messageForm button[type="submit"]');
    if (aiToggle && messageInput && sendBtn) {
        if (aiToggle.checked) {
            messageInput.disabled = true;
            sendBtn.disabled = true;
        } else {
            messageInput.disabled = false;
            sendBtn.disabled = false;
        }
    }
}

function addKeyword(contactId, keyword, replacement) {
    if (!contactId || !keyword) return;
    
    fetch('/api/add_keyword', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            contact_id: contactId,
            keyword: keyword,
            replacement: replacement
        }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('成功', '关键词已添加');
            loadKeywords(contactId);
        } else {
            showToast('错误', data.error || '添加失败');
        }
    })
    .catch(error => {
        console.error('添加关键词失败:', error);
        showToast('错误', '添加失败');
    });
}

function editKeyword(keywordId, keyword, replacement) {
    document.getElementById('editKeywordId').value = keywordId;
    document.getElementById('editKeywordText').value = keyword || '';
    document.getElementById('editKeywordReplacement').value = replacement || '';
    
    const editKeywordModal = new bootstrap.Modal(document.getElementById('editKeywordModal'));
    editKeywordModal.show();
}

function updateKeyword(keywordId, keyword, replacement) {
    if (!keywordId || !keyword) return;
    
    fetch('/api/update_keyword', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            keyword_id: keywordId,
            keyword: keyword,
            replacement: replacement
        }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('成功', '关键词已更新');
            loadKeywords(currentContactId);
        } else {
            showToast('错误', data.error || '更新失败');
        }
    })
    .catch(error => {
        console.error('更新关键词失败:', error);
        showToast('错误', '更新失败');
    });
}

function deleteKeyword(keywordId) {
    document.getElementById('deleteKeywordId').value = keywordId;
    
    const deleteKeywordModal = new bootstrap.Modal(document.getElementById('deleteKeywordModal'));
    deleteKeywordModal.show();
}

function confirmDeleteKeyword(keywordId) {
    if (!keywordId) return;
    
    fetch('/api/delete_keyword', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            keyword_id: keywordId
        }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('成功', '关键词已删除');
            loadKeywords(currentContactId);
        } else {
            showToast('错误', data.error || '删除失败');
        }
    })
    .catch(error => {
        console.error('删除关键词失败:', error);
        showToast('错误', '删除失败');
    });
}
function onAccountSelected(newWechatId) {
    currentWechatId = newWechatId;
    window.currentWechatId = newWechatId;
    
    if (window.globalSocket && window.globalSocket.connected) {
        window.globalSocket.emit('join_wechat_room', {
            user_id: window.userId,
            wechat_id: newWechatId
        });
    }
    
    updateCurrentAccountInfo(newWechatId);
    loadContacts(newWechatId);
}

function showToast(title, message) {
    const toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) return;
    
    const toastId = 'toast-' + Date.now();
    const toastHtml = `
        <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header">
                <strong class="me-auto">${title}</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, { delay: 3000 });
    toast.show();
    
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}

async function initWebSocket() {
    console.log('联系人页面WebSocket初始化');
    
    if (window.globalSocket && window.globalSocket.connected) {
        console.log('使用全局WebSocket连接');
        window.currentSocket = window.globalSocket;
        setupContactsWebSocketHandlers();
        

        return;
    }

    console.log('全局WebSocket未就绪，等待初始化');
    setTimeout(initWebSocket, 500);
}

function setupContactsWebSocketHandlers() {
    const socket = window.currentSocket;
    if (!socket) return;

    socket.off('new_message');
    socket.on('new_message', function (data) {
        console.log('联系人页面收到 new_message:', data);
        
        if (data.message_id && document.getElementById(data.message_id)) return;

        if (data.contact_id === currentContactId) {
            const messagesContainer = document.getElementById('messagesContainer');

            let isFromMe = false;
            if (data.send_type) {
                isFromMe = data.send_type === 'active';
            } else {
                isFromMe = data.sender_id === currentWechatId;
            }

            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${isFromMe ? 'message-sent' : 'message-received'}`;
            if (data.message_id) {
                messageDiv.id = data.message_id;
            }

            let messageContent = '';
            if (data.content_type === 'text') {
                messageContent = `<div class="message-text">${data.content}</div>`;
            } else if (data.content_type === 'image') {
                messageContent = `<div class="message-image"><img src="${data.image_url}" alt="图片消息" class="img-fluid rounded"></div>`;
            } else {
                messageContent = `<div class="message-text">[${data.content_type}消息]</div>`;
            }

            messageDiv.innerHTML = `
                <div class="message-content">
                    ${messageContent}
                    <div class="message-time">${formatTime(data.created_at)}</div>
                </div>
            `;

            messagesContainer.appendChild(messageDiv);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;

            if (data.send_type === 'passive' && shouldPlayNotificationSound(data.contact_id)) {
                playNotificationSound();
            }
        } else {
            if (data.send_type === 'passive' && shouldPlayNotificationSound(data.contact_id)) {
                playNotificationSound();
            }
        }

        updateContactLastMessage(data.contact_id, data.content, data.created_at, data.send_type);
    });
}

function updateContactLastMessage(contactId, message, time, sendType) {
    const contact = contacts.find(c => c.wechat_id === contactId);
    if (contact) {
        contact.last_message = message;
        contact.last_message_time = time;
        
        contacts.sort((a, b) => {
            const ta = a.last_message_time || a.last_sync_time || 0;
            const tb = b.last_message_time || b.last_sync_time || 0;
            return new Date(tb) - new Date(ta);
        });
        
        renderContacts(contacts, 1, 10);
    }
    
    const contactItem = document.querySelector(`.contact-item[data-wechat-id="${contactId}"]`);
    if (contactItem) {
        const lastMessageElement = contactItem.querySelector('.contact-last-msg');
        const timeElement = contactItem.querySelector('.contact-time');
        if (lastMessageElement) {
            lastMessageElement.textContent = message;
        }
        if (timeElement) {
            timeElement.textContent = formatTime(time);
        }
        if (contactId !== currentContactId && sendType === 'passive') {
            const badgeElement = contactItem.querySelector('.badge');
            if (badgeElement) {
                const currentCount = parseInt(badgeElement.textContent) || 0;
                badgeElement.textContent = currentCount + 1;
                badgeElement.classList.remove('d-none');
            } else {
                const badgeContainer = contactItem.querySelector('.contact-info');
                if (badgeContainer) {
                    const badge = document.createElement('span');
                    badge.className = 'badge bg-danger rounded-pill ms-2';
                    badge.textContent = '1';
                    badgeContainer.appendChild(badge);
                }
            }
        }
        const contactsList = document.getElementById('contactsList');
        if (contactsList && contactsList.firstChild) {
            contactsList.insertBefore(contactItem, contactsList.firstChild);
        }
    }
    // ===== 新增：同步 contacts 数据和置顶 =====
    let idx = contacts.findIndex(c => c.id == contactId || c.wechat_id == contactId);
    if (idx !== -1) {
        contacts[idx].last_message = message;
        contacts[idx].last_message_time = time;

        if (contactId !== currentContactId && sendType === 'passive') {
            contacts[idx].unread_count = (contacts[idx].unread_count || 0) + 1;
        } else {
            contacts[idx].unread_count = 0;
        }
        // 置顶到第一位
        const contactObj = contacts.splice(idx, 1)[0];
        contacts.unshift(contactObj);
    }
	 const index = contacts.findIndex(c => c.id === contactId || c.wechat_id === contactId);
    if (index !== -1) {
        const updatedContact = contacts.splice(index, 1)[0];
        updatedContact.last_message = message;
        updatedContact.last_message_time = time;
        contacts.unshift(updatedContact);
    }
    // 然后重新渲染
    renderContacts(contacts, 1, 10);
}


function shouldPlayNotificationSound(contactId) {
    const contact = contacts.find(c => c.id === contactId);
    if (contact && contact.ai_reply_enabled) {
        return false; // AI开启时不播放提示音
    }
    
    if (document.hasFocus() && contactId === currentContactId) {
        return false; // 当前聊天窗口聚焦时不播放
    }
    
    return true;
}


function playNotificationSound() {
    const audio = document.getElementById('notificationSound');
    if (!audio) {
        console.log('未找到提示音audio标签');
        return;
    }
    audio.currentTime = 0;
    const playPromise = audio.play();
    if (playPromise) {
        playPromise.catch(e => {
            console.log('播放提示音失败:', e);
        });
    }
}




function clearUnreadCount(contactId) {
    const contactItem = document.querySelector(`.contact-item[data-id="${contactId}"]`);
    if (contactItem) {
        const badgeElement = contactItem.querySelector('.badge');
        if (badgeElement) {
            badgeElement.textContent = '0';
            badgeElement.classList.add('d-none');
        }
        
        fetch(`/api/contacts/${contactId}/clear_unread`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            console.log('清除未读计数成功:', data);
        })
        .catch(error => {
            console.error('清除未读计数失败:', error);
        });
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // ...已有初始化

    // AI回复开关逻辑
    const aiToggle = document.getElementById('chatAiReplyToggle');
    const messageInput = document.getElementById('messageInput');
    const sendBtn = document.querySelector('#messageForm button[type="submit"]');
    if (aiToggle && messageInput && sendBtn) {
        aiToggle.addEventListener('change', function() {
            if (aiToggle.checked) {
                messageInput.disabled = true;
                sendBtn.disabled = true;
            } else {
                messageInput.disabled = false;
                sendBtn.disabled = false;
            }
        });
        // 页面初始时同步一次
        if (aiToggle.checked) {
            messageInput.disabled = true;
            sendBtn.disabled = true;
        }
    }
});

// ========== 图片、文件、表情按钮事件绑定 ==========
document.addEventListener('DOMContentLoaded', function () {
    // 图片按钮
    const uploadImageBtn = document.getElementById('uploadImageBtn');
    if (uploadImageBtn) {
        uploadImageBtn.addEventListener('click', function () {
            if (!currentContactId) {
                showToast('提示', '请先选择一个联系人');
                return;
            }

            // 示例：触发文件选择框
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = 'image/*'; // 只允许图片
            input.onchange = function (e) {
                const file = e.target.files[0];
                if (file) {
                    console.log('选中的图片:', file);
                    // TODO: 在这里调用发送图片消息的方法
                }
            };
            input.click();
        });
    }

    // 文件按钮
    const uploadFileBtn = document.getElementById('uploadFileBtn');
    if (uploadFileBtn) {
        uploadFileBtn.addEventListener('click', function () {
            if (!currentContactId) {
                showToast('提示', '请先选择一个联系人');
                return;
            }

            const input = document.createElement('input');
            input.type = 'file';
            input.onchange = function (e) {
                const file = e.target.files[0];
                if (file) {
                    console.log('选中的文件:', file);
                    // TODO: 在这里调用发送文件消息的方法
                }
            };
            input.click();
        });
    }

    // 表情按钮
    const emojiBtn = document.getElementById('emojiBtn');
    if (emojiBtn) {
        emojiBtn.addEventListener('click', function () {
            //alert('打开表情面板（需要集成表情库）');
            // TODO: 打开表情面板，插入表情到输入框
        });
    }
});

// 微信风格常用 emoji 表情库
const wechatEmojis = [
    "😀", "😃", "😄", "😁", "😆", "😅", "😂", "🤣", "😊", "😇",
    "🙂", "🙃", "😉", "😌", "😍", "😘", "😗", "😙", "😚", "😋",
    "😜", "😝", "😛", "🤑", "🤓", "😎", "🥳", "🥺", "😏", "😒",
    "😞", "😔", "😟", "😕", "🙁", "☹️", "😣", "😖", "😫", "😩",
    "😤", "😠", "😡", "🤬", "🤯", "😳", "😱", "😨", "😰", "😥"
];

// 初始化表情面板内容
function initEmojiPanel() {
    const emojiRow = document.querySelector('.emoji-row');
    emojiRow.innerHTML = '';
    wechatEmojis.forEach(emoji => {
        const span = document.createElement('span');
        span.className = 'emoji-item';
        span.textContent = emoji;
        span.title = emoji;
        span.addEventListener('click', function () {
            insertAtCursor(document.getElementById('messageInput'), emoji);
            hideEmojiPanel();
        });
        emojiRow.appendChild(span);
    });
}

// 插入表情到输入框光标位置
function insertAtCursor(input, text) {
    if (!input) return;
    const start = input.selectionStart || 0;
    const end = input.selectionEnd || 0;
    const value = input.value;
    input.value = value.substring(0, start) + text + value.substring(end);
    input.focus();
    input.selectionStart = input.selectionEnd = start + text.length;
    input.dispatchEvent(new Event('input')); // 触发自动调整高度
}

// 显示/隐藏表情面板
function showEmojiPanel() {
    const panel = document.getElementById('emojiPanel');
    if (panel) panel.style.display = 'block';
}

function hideEmojiPanel() {
    const panel = document.getElementById('emojiPanel');
    if (panel) panel.style.display = 'none';
}

// 点击其他区域关闭表情面板
document.addEventListener('click', function (e) {
    const panel = document.getElementById('emojiPanel');
    const btn = document.getElementById('emojiBtn');
    if (panel && !panel.contains(e.target) && !btn?.contains(e.target)) {
        hideEmojiPanel();
    }
});

// 绑定表情按钮点击事件
document.getElementById('emojiBtn')?.addEventListener('click', function () {
    if (document.getElementById('emojiPanel').style.display === 'block') {
        hideEmojiPanel();
    } else {
        showEmojiPanel();
    }
});

// 页面加载时初始化表情面板
document.addEventListener('DOMContentLoaded', initEmojiPanel);
