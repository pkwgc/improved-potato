/**
 * 全局WebSocket连接管理器
 * 负责维护跨页面的WebSocket连接，自动重连和消息恢复
 */
class GlobalWebSocketManager {
    constructor() {
        this.socket = null;
        this.isConnected = false;
        this.isAuthenticated = false;
        this.userId = null;
        this.currentWechatId = null;
        this.joinedRooms = new Set();
        this.messageQueue = [];
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.heartbeatInterval = null;
        this.connectionStateKey = 'websocket_connection_state';
        
        this.init();
    }
    
    init() {
        this.restoreConnectionState();
        
        if (this.userId) {
            this.connect();
        }
        
        window.addEventListener('beforeunload', () => {
            this.saveConnectionState();
        });
        
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && !this.isConnected) {
                this.reconnect();
            }
        });
    }
    
    async connect() {
        if (this.socket && this.isConnected) {
            return;
        }
        
        try {
            const response = await fetch('/api/websocket_config');
            const config = await response.json();
            
            this.socket = io(config.enabled ? undefined : 'http://localhost:5001');
            
            this.setupEventHandlers();
            
        } catch (error) {
            console.error('WebSocket配置获取失败:', error);
            this.socket = io();
            this.setupEventHandlers();
        }
    }
    
    setupEventHandlers() {
        this.socket.on('connect', () => {
            console.log('全局WebSocket连接成功');
            this.isConnected = true;
            this.reconnectAttempts = 0;
            
            if (this.userId) {
                this.authenticate();
            }
            
            window.dispatchEvent(new CustomEvent('websocket-connected'));
        });
        
        this.socket.on('disconnect', () => {
            console.log('全局WebSocket连接断开');
            this.isConnected = false;
            this.isAuthenticated = false;
            this.stopHeartbeat();
            
            window.dispatchEvent(new CustomEvent('websocket-disconnected'));
            
            this.scheduleReconnect();
        });
        
        this.socket.on('auth_success', (data) => {
            console.log('全局WebSocket认证成功:', data);
            this.isAuthenticated = true;
            
            this.rejoinRooms();
            
            this.startHeartbeat();
            
            this.processMessageQueue();
            
            window.dispatchEvent(new CustomEvent('websocket-authenticated', { detail: data }));
        });
        
        this.socket.on('authenticated', (data) => {
            console.log('全局WebSocket认证成功(authenticated):', data);
            this.isAuthenticated = true;
            
            this.rejoinRooms();
            
            this.startHeartbeat();
            
            this.processMessageQueue();
            
            window.dispatchEvent(new CustomEvent('websocket-authenticated', { detail: data }));
        });
        
        this.socket.on('joined_wechat_room', (data) => {
            console.log('已加入微信房间:', data);
            this.joinedRooms.add(data.wechat_id);
            this.saveConnectionState();
            
            window.dispatchEvent(new CustomEvent('websocket-room-joined', { detail: data }));
        });
        
        this.socket.on('new_message', (data) => {
            console.log('收到全局消息:', data);
            
            window.dispatchEvent(new CustomEvent('websocket-message', { detail: data }));
            
            if (data.id && data.require_ack) {
                this.acknowledgeMessage(data.id);
            }
        });
        
        this.socket.on('heartbeat_ack', (data) => {
            console.log('收到心跳确认:', data);
        });
        
        this.socket.on('heartbeat_response', (data) => {
            console.log('收到心跳响应:', data);
        });
        
        this.socket.on('error', (data) => {
            console.error('全局WebSocket错误:', data);
            
            if (data.code === 'auth_required') {
                this.isAuthenticated = false;
                if (this.userId) {
                    this.authenticate();
                }
            }
            
            window.dispatchEvent(new CustomEvent('websocket-error', { detail: data }));
        });
    }
    
    authenticate() {
        if (!this.socket || !this.isConnected || !this.userId) {
            return;
        }
        
        console.log('发送全局认证:', this.userId);
        this.socket.emit('authenticate', { user_id: this.userId });
    }
    
    joinWechatRoom(wechatId) {
        if (!this.socket || !this.isAuthenticated) {
            console.warn('WebSocket未认证，无法加入房间');
            return;
        }
        
        this.currentWechatId = wechatId;
        this.socket.emit('join_wechat_room', {
            user_id: this.userId,
            wechat_id: wechatId
        });
    }
    
    rejoinRooms() {
        this.joinedRooms.forEach(wechatId => {
            this.joinWechatRoom(wechatId);
        });
        
        if (this.currentWechatId) {
            this.joinWechatRoom(this.currentWechatId);
        }
    }
    
    startHeartbeat() {
        this.stopHeartbeat();
        
        this.heartbeatInterval = setInterval(() => {
            if (this.socket && this.isConnected && this.isAuthenticated) {
                this.socket.emit('heartbeat', { 
                    user_id: this.userId,
                    timestamp: new Date().toISOString()
                });
            }
        }, 15000);
    }
    
    stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }
    
    acknowledgeMessage(messageId) {
        if (this.socket && this.isAuthenticated) {
            this.socket.emit('message_ack', {
                user_id: this.userId,
                message_id: messageId
            });
        }
    }
    
    sendMessage(data) {
        if (this.socket && this.isAuthenticated) {
            this.socket.emit('send_direct_message', data);
        } else {
            this.messageQueue.push(data);
        }
    }
    
    processMessageQueue() {
        while (this.messageQueue.length > 0) {
            const message = this.messageQueue.shift();
            this.sendMessage(message);
        }
    }
    
    scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('达到最大重连次数，停止重连');
            return;
        }
        
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts);
        console.log(`${delay}ms后尝试重连...`);
        
        setTimeout(() => {
            this.reconnect();
        }, delay);
        
        this.reconnectAttempts++;
    }
    
    reconnect() {
        if (this.socket) {
            this.socket.disconnect();
        }
        
        this.isConnected = false;
        this.isAuthenticated = false;
        this.socket = null;
        
        this.connect();
    }
    
    saveConnectionState() {
        const state = {
            userId: this.userId,
            currentWechatId: this.currentWechatId,
            joinedRooms: Array.from(this.joinedRooms),
            timestamp: Date.now()
        };
        
        localStorage.setItem(this.connectionStateKey, JSON.stringify(state));
    }
    
    restoreConnectionState() {
        try {
            const stateStr = localStorage.getItem(this.connectionStateKey);
            if (stateStr) {
                const state = JSON.parse(stateStr);
                
                if (Date.now() - state.timestamp < 3600000) {
                    this.userId = state.userId;
                    this.currentWechatId = state.currentWechatId;
                    this.joinedRooms = new Set(state.joinedRooms || []);
                }
            }
        } catch (error) {
            console.error('恢复连接状态失败:', error);
        }
    }
    
    setUserId(userId) {
        this.userId = userId;
        this.saveConnectionState();
        
        if (!this.isConnected) {
            this.connect();
        } else if (!this.isAuthenticated) {
            this.authenticate();
        }
    }
    
    disconnect() {
        this.stopHeartbeat();
        
        if (this.socket) {
            this.socket.disconnect();
        }
        
        this.isConnected = false;
        this.isAuthenticated = false;
        this.socket = null;
        
        localStorage.removeItem(this.connectionStateKey);
    }
}

if (!window.globalWebSocket) {
    console.log('初始化全局WebSocket管理器');
    window.globalWebSocket = new GlobalWebSocketManager();
} else {
    console.log('全局WebSocket管理器已存在，跳过重复初始化');
}
