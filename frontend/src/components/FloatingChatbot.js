import React, { useState, useRef, useEffect } from 'react';
import Message from './Message';
import MessageInput from './MessageInput';

function FloatingChatbot({ 
  messages, 
  onSend, 
  isLoading, 
  sessionId, 
  showSources, 
  toggleSources, 
  inputMessage, 
  setInputMessage, 
  handleKeyPress, 
  loadChatHistory, 
  clearChatHistory, 
  createNewSession 
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isMinimized, setIsMinimized] = useState(true);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const toggleChat = () => {
    if (isMinimized) {
      setIsMinimized(false);
      setIsExpanded(false);
    } else if (!isExpanded) {
      setIsExpanded(true);
    } else {
      setIsMinimized(true);
    }
  };

  const minimizeChat = () => {
    setIsExpanded(false);
    setIsMinimized(true);
  };

  const expandChat = () => {
    setIsExpanded(true);
    setIsMinimized(false);
  };

  return (
    <div className="fixed bottom-4 right-4 z-50">
      {/* Minimized Chat Button */}
      {isMinimized && (
        <button
          onClick={toggleChat}
          className="bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white rounded-full p-4 shadow-lg transition-all duration-300 hover:scale-110 bounce-in"
          title="Mở chatbot"
        >
          <div className="flex items-center space-x-2">
            <span className="text-2xl">🤖</span>
            <span className="text-sm font-medium">Chat</span>
          </div>
        </button>
      )}

      {/* Chat Window */}
      {!isMinimized && (
        <div className={`bg-white rounded-lg shadow-xl border transition-all duration-300 ${
          isExpanded 
            ? 'w-96 h-[600px]' 
            : 'w-80 h-[500px]'
        }`}>
          {/* Header */}
          <div className="flex justify-between items-center p-4 border-b bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-t-lg">
            <div className="flex items-center space-x-2">
              <span className="text-xl">🤖</span>
              <div>
                <h3 className="font-semibold">Trợ lý Ảo</h3>
                <p className="text-xs opacity-90">Chính phủ điện tử</p>
              </div>
            </div>
            <div className="flex items-center space-x-1">
              {!isExpanded && (
                <button
                  onClick={expandChat}
                  className="p-1 hover:bg-blue-800 rounded transition-colors"
                  title="Mở rộng"
                >
                  ⬜
                </button>
              )}
              {isExpanded && (
                <button
                  onClick={minimizeChat}
                  className="p-1 hover:bg-blue-800 rounded transition-colors"
                  title="Thu nhỏ"
                >
                  ⬛
                </button>
              )}
              <button
                onClick={toggleChat}
                className="p-1 hover:bg-blue-800 rounded transition-colors"
                title="Đóng"
              >
                ✕
              </button>
            </div>
          </div>

          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3 chat-messages" style={{ height: isExpanded ? '450px' : '350px' }}>
            {messages.length === 0 && !isLoading && (
              <div className="text-center text-gray-500 py-6">
                <span className="text-3xl block mb-2">🤖</span>
                <p className="text-sm font-medium">Chào mừng bạn!</p>
                <p className="text-xs text-gray-400 mt-1">Tôi là trợ lý ảo của Chính phủ điện tử</p>
                <p className="text-xs text-gray-400">Hãy đặt câu hỏi để được hỗ trợ</p>
              </div>
            )}
            {messages.map((message) => (
              <Message 
                key={message.id} 
                message={message} 
                showSources={showSources} 
                toggleSources={toggleSources} 
              />
            ))}
            {/* Loading indicator giữ chỗ, không làm giật khung */}
            <div style={{ minHeight: isLoading ? 32 : 0 }}>
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 rounded-lg p-2 max-w-xs animate-pulse">
                    <span className="text-sm">🤖 Đang trả lời...</span>
                  </div>
                </div>
              )}
            </div>
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="p-3 border-t bg-gray-50">
            <MessageInput
              inputMessage={inputMessage}
              setInputMessage={setInputMessage}
              handleKeyPress={handleKeyPress}
              onSend={onSend}
              isLoading={isLoading}
            />
          </div>

          {/* Expanded Controls: chỉ giữ lại sessionId */}
          {isExpanded && (
            <div className="p-3 border-t bg-gray-50 flex justify-end items-center">
              <span className="text-xs text-gray-500">
                {sessionId?.substring(0, 8)}...
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default FloatingChatbot; 