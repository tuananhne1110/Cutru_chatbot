import React, { useRef, useEffect } from 'react';

function MessageInput({ inputMessage, setInputMessage, handleKeyPress, onSend, isLoading, onVoiceInput, isVoiceStreaming }) {
  const textareaRef = useRef(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 120) + 'px'; // tối đa ~5 dòng
    }
  }, [inputMessage]);

  // Sử dụng onKeyDown để phân biệt Enter và Shift+Enter
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  return (
    <div className="flex gap-2 items-center">
      <div className="flex-1 relative">
        <input
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Nhập câu hỏi..."
          className={`w-full px-4 py-2 border border-gray-300 rounded-full text-sm outline-none transition-colors focus:border-blue-500 ${
            isVoiceStreaming ? 'border-green-400 bg-green-50' : ''
          }`}
          disabled={isLoading}
        />
        {/* Voice streaming indicator */}
        {isVoiceStreaming && (
          <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
            <div className="flex space-x-1">
              <div className="w-1 h-3 bg-green-500 rounded-full animate-bounce"></div>
              <div className="w-1 h-3 bg-green-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
              <div className="w-1 h-3 bg-green-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
            </div>
          </div>
        )}
      </div>
      
      {/* Voice Input Button */}
      <button
        onClick={onVoiceInput}
        disabled={isLoading}
        className={`border-none w-9 h-9 rounded-full cursor-pointer flex items-center justify-center text-sm disabled:opacity-50 disabled:cursor-not-allowed transition-all ${
          isVoiceStreaming 
            ? 'bg-green-500 text-white animate-pulse' 
            : 'bg-gradient-to-br from-green-500 to-green-600 text-white hover:scale-105'
        }`}
        title="Nhập bằng giọng nói"
      >
        🎤
      </button>
      
      <button
        onClick={onSend}
        disabled={!inputMessage.trim() || isLoading}
        className="bg-gradient-to-br from-blue-500 to-purple-600 text-white border-none w-9 h-9 rounded-full cursor-pointer flex items-center justify-center text-sm disabled:opacity-50 disabled:cursor-not-allowed"
      >
        ➤
      </button>
    </div>
  );
}

export default MessageInput; 