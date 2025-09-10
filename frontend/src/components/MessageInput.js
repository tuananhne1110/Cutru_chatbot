import React, { useRef, useEffect } from 'react';

function MessageInput({ inputMessage, setInputMessage, handleKeyPress, onSend, isLoading, onVoiceChat, onUploadFiles }) {
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

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
          className="w-full px-4 py-2 border border-gray-300 rounded-full text-sm outline-none transition-colors focus:border-blue-500"
          disabled={isLoading}
        />
      </div>
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        className="hidden"
        onChange={(e) => {
          const files = Array.from(e.target.files || []);
          if (files.length && onUploadFiles) {
            onUploadFiles(files);
          }
          // reset value to allow uploading same file again
          e.target.value = '';
        }}
      />

      {/* Upload Button */}
      <button
        onClick={() => fileInputRef.current && fileInputRef.current.click()}
        disabled={isLoading}
        className="bg-gray-100 text-gray-700 border-none w-9 h-9 rounded-full cursor-pointer flex items-center justify-center text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-200 transition-all"
        title="Tải tài liệu lên"
      >
        📎
      </button>
      
      {/* Voice Chat Button */}
      <button
        onClick={onVoiceChat}
        disabled={isLoading}
        className="bg-gradient-to-br from-purple-500 to-blue-600 text-white border-none w-9 h-9 rounded-full cursor-pointer flex items-center justify-center text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:scale-105 transition-all"
        title="Mở Voice Chat"
      >
        🎤
      </button>
      
      <button
        onClick={onSend}
        disabled={!inputMessage || !inputMessage.trim() || isLoading}
        className="bg-gradient-to-br from-blue-500 to-purple-600 text-white border-none w-9 h-9 rounded-full cursor-pointer flex items-center justify-center text-sm disabled:opacity-50 disabled:cursor-not-allowed"
      >
        ➤
      </button>
    </div>
  );
}

export default MessageInput; 