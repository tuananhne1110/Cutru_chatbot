import React, { useRef, useEffect } from 'react';

function MessageInput({ inputMessage, setInputMessage, handleKeyPress, onSend, isLoading }) {
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
    <div className="flex space-x-2 items-end">
      <textarea
        ref={textareaRef}
        value={inputMessage}
        onChange={(e) => setInputMessage(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Nhập câu hỏi..."
        className="flex-1 border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm min-h-[40px] max-h-[120px] resize-none"
        disabled={isLoading}
        rows={2}
        maxLength={1000}
        style={{lineHeight: '1.5', whiteSpace: 'pre-wrap', overflowWrap: 'break-word'}}
        wrap="soft"
      />
      <button
        onClick={onSend}
        disabled={!inputMessage.trim() || isLoading}
        className="bg-blue-600 text-white p-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center min-w-[40px]"
      >
        <span role="img" aria-label="send">📤</span>
      </button>
    </div>
  );
}

export default MessageInput; 