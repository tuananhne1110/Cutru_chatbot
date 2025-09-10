import React from 'react';

function VoiceTypingIndicator({ isStreaming, text }) {
  if (!isStreaming || !text) {
    return null;
  }

  return (
    <div className="px-4 py-2 bg-green-50 border-b border-green-200">
      <div className="flex items-center text-green-700 text-sm">
        <div className="flex space-x-1 mr-2">
          <div className="w-1 h-3 bg-green-500 rounded-full animate-bounce"></div>
          <div className="w-1 h-3 bg-green-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
          <div className="w-1 h-3 bg-green-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
        </div>
        <span className="font-medium">🎤 Đang nhận diện giọng nói:</span>
        <span className="ml-2 italic">"{text}"</span>
      </div>
    </div>
  );
}

export default VoiceTypingIndicator;
