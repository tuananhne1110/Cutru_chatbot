import React, { useRef, useEffect } from 'react';
import Message from './Message';
import MessageInput from './MessageInput';

function ChatWindow({ messages, onSend, isLoading, sessionId, showSources, toggleSources, inputMessage, setInputMessage, handleKeyPress }) {
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      <div className="bg-white rounded-lg shadow-sm border h-[600px] flex flex-col">
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && !isLoading && (
            <div className="text-center text-gray-500 py-8">
              <span role="img" aria-label="bot" className="text-4xl">🤖</span>
              <p>Xin chào! Tôi là trợ lý pháp luật.</p>
              <p className="text-sm">Hãy đặt câu hỏi về luật pháp Việt Nam.</p>
            </div>
          )}
          {messages.map((message) => (
            <Message key={message.id} message={message} showSources={showSources} toggleSources={toggleSources} />
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 rounded-lg p-3">
                <span role="img" aria-label="bot">🤖</span>
                <span className="ml-2">Đang trả lời...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
        <MessageInput
          inputMessage={inputMessage}
          setInputMessage={setInputMessage}
          handleKeyPress={handleKeyPress}
          onSend={onSend}
          isLoading={isLoading}
        />
      </div>
    </div>
  );
}

export default ChatWindow; 