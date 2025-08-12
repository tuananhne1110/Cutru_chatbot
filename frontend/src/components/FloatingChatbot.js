import React, { useState, useRef, useEffect } from 'react';
import Message from './Message';
import MessageInput from './MessageInput';
import CT01Modal from './CT01Modal';
import VoiceRecorder from './VoiceRecorder';
import VoiceSupportInfo from './VoiceSupportInfo';
import VoiceTypingIndicator from './VoiceTypingIndicator';
import useVoiceToText from '../hooks/useVoiceToText';

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
  createNewSession,
  openCT01Modal
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isMinimized, setIsMinimized] = useState(true);
  const [isCT01ModalOpen, setIsCT01ModalOpen] = useState(false);
  const messagesEndRef = useRef(null);

  // Voice-to-text hook
  const {
    isRecording,
    isLoading: voiceLoading,
    error: voiceError,
    currentText: voiceText,
    toggleRecording,
    stopRecording
  } = useVoiceToText((text) => {
    setInputMessage(text);
  });

  // Auto-send message when recording stops
  useEffect(() => {
    if (!isRecording && voiceText && voiceText.trim()) {
      // Small delay to ensure text is properly set
      const timer = setTimeout(() => {
        if (inputMessage && inputMessage.trim()) {
          onSend();
        }
      }, 300);
      
      return () => clearTimeout(timer);
    }
  }, [isRecording, voiceText, inputMessage, onSend]);

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

  // Removed unused functions to fix ESLint warnings

  const handleChatMessage = (message) => {
    // This would need to be handled by the parent component
    // For now, we'll just log it
  };

  const closeCT01Modal = () => {
    setIsCT01ModalOpen(false);
  };

  return (
    <div className="fixed bottom-5 right-5 z-[2500] transition-all duration-300">
      {/* Minimized Chat Button - y hệt như UI.html */}
      {isMinimized && (
        <button
          onClick={toggleChat}
          className="w-15 h-15 bg-gradient-to-br from-blue-500 to-purple-600 border-none rounded-full text-white text-2xl cursor-pointer shadow-lg transition-all duration-300 hover:scale-110 flex items-center justify-center"
          title="Mở chatbot"
        >
          🤖
        </button>
      )}

      {/* Chat Window - y hệt như UI.html */}
      {!isMinimized && (
        <div className={`absolute bottom-16 right-0 w-[350px] h-[500px] bg-white rounded-2xl shadow-2xl border transition-all duration-300 ${
          isExpanded ? 'w-96 h-[600px]' : 'w-[350px] h-[500px]'
        }`}>
          {/* Header */}
          <div className="bg-gradient-to-br from-blue-500 to-purple-600 text-white p-4 rounded-t-2xl flex justify-between items-center">
            <div className="text-base font-semibold">🤖 Trợ lý Ảo</div>
            <button
              onClick={toggleChat}
              className="bg-transparent border-none text-white text-xl cursor-pointer w-6 h-6 rounded-full flex items-center justify-center"
            >
              ×
            </button>
          </div>

          {/* Messages Area - y hệt như UI.html */}
          <div className="flex-1 p-4 overflow-y-auto bg-gray-50" style={{ height: isExpanded ? '450px' : '350px' }}>
            {messages.length === 0 && !isLoading && (
              <div className="text-center text-gray-500 py-6">
                <span className="text-3xl block mb-2">🤖</span>
                <p className="text-sm font-medium">Chào mừng bạn!</p>
                <p className="text-xs text-gray-400 mt-1">Tôi là trợ lý ảo của Chính phủ điện tử</p>
                <p className="text-xs text-gray-400 mb-4">Hãy đặt câu hỏi để được hỗ trợ</p>
                
                {/* Suggestion chips - y hệt như UI.html */}
                <div className="flex flex-wrap gap-2 justify-center">
                  <button 
                    onClick={() => {
                      onSend('Điền biểu mẫu CT01');
                      // Mở modal ngay lập tức
                      setTimeout(() => {
                        openCT01Modal();
                      }, 500);
                    }}
                    className="bg-gray-200 border-none px-3 py-1 rounded-full text-xs cursor-pointer transition-all duration-200 hover:bg-blue-500 hover:text-white"
                  >
                    📝 Điền CT01
                  </button>
                  <button 
                    onClick={() => onSend('Tra cứu thủ tục')}
                    className="bg-gray-200 border-none px-3 py-1 rounded-full text-xs cursor-pointer transition-all duration-200 hover:bg-blue-500 hover:text-white"
                  >
                    🔍 Tra cứu
                  </button>
                  <button 
                    onClick={() => onSend('Hướng dẫn')}
                    className="bg-gray-200 border-none px-3 py-1 rounded-full text-xs cursor-pointer transition-all duration-200 hover:bg-blue-500 hover:text-white"
                  >
                    ❓ Hướng dẫn
                  </button>
                </div>
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
            {/* Loading indicator */}
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

          {/* Voice Typing Indicator */}
          <VoiceTypingIndicator 
            isStreaming={isRecording && voiceText && voiceText.trim()} 
            text={voiceText} 
          />

          {/* Input Area - y hệt như UI.html */}
          <div className="p-4 bg-white border-t border-gray-200">
            <VoiceRecorder
              isRecording={isRecording}
              currentText={voiceText}
              error={voiceError}
              onStop={stopRecording}
            />
            
            <MessageInput
              inputMessage={inputMessage}
              setInputMessage={setInputMessage}
              handleKeyPress={handleKeyPress}
              onSend={onSend}
              isLoading={isLoading || voiceLoading}
              onVoiceInput={toggleRecording}
              isVoiceStreaming={isRecording && voiceText && voiceText.trim()}
            />
            <VoiceSupportInfo />
          </div>
        </div>
      )}

      {/* CT01 Modal */}
      <CT01Modal
        isOpen={isCT01ModalOpen}
        onClose={closeCT01Modal}
        onChatMessage={handleChatMessage}
      />
    </div>
  );
}

export default FloatingChatbot; 