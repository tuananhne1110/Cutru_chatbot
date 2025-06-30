import React from 'react';

function MessageInput({ inputMessage, setInputMessage, handleKeyPress, onSend, isLoading }) {
  return (
    <div className="border-t p-4">
      <div className="flex space-x-2">
        <textarea
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Nhập câu hỏi về luật pháp..."
          className="flex-1 border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
          rows="2"
          disabled={isLoading}
        />
        <button
          onClick={onSend}
          disabled={!inputMessage.trim() || isLoading}
          className="bg-blue-600 text-white p-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
        >
          <span role="img" aria-label="send">📤</span>
        </button>
      </div>
      <div className="text-xs text-gray-500 mt-2">
        Nhấn Enter để gửi, Shift+Enter để xuống dòng
      </div>
    </div>
  );
}

export default MessageInput; 