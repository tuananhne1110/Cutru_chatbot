import React from 'react';

const VoiceTypingIndicator = ({ isStreaming, text }) => {
  if (!isStreaming || !text) return null;

  return (
    <div className="flex items-center gap-2 text-xs text-green-600 bg-green-50 px-3 py-2 rounded-lg border border-green-200">
      <div className="flex space-x-1">
        <div className="w-1 h-3 bg-green-500 rounded-full animate-bounce"></div>
        <div className="w-1 h-3 bg-green-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
        <div className="w-1 h-3 bg-green-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
      </div>
      <span>🎤 Đang ghi âm...</span>
      <span className="text-gray-600">"{text}"</span>
    </div>
  );
};

export default VoiceTypingIndicator;
