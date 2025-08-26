import React, { useEffect, useState } from 'react';
import { Routes, Route, useNavigate } from 'react-router-dom';
import FloatingChatbot from './components/FloatingChatbot';
import CT01TestPage from './components/CT01TestPage';
import useChatStream from './hooks/useChatStream';
import CT01Modal from './components/CT01Modal';
import VoiceCallPage from './pages/VoiceCallPage';
import axios from 'axios';

// Use relative paths for proxy to work correctly
const API_BASE_URL = '';

function App() {
  const navigate = useNavigate();
  const [sessionId, setSessionId] = useState(() => {
    // Kiểm tra localStorage trước
    const savedSessionId = localStorage.getItem('chatSessionId');
    return savedSessionId || null;
  });
  
  const [isCT01ModalOpen, setIsCT01ModalOpen] = useState(false);
  
  const {
    messages,
    setMessages,
    inputMessage,
    setInputMessage: originalSetInputMessage,
    isLoading,
    sendMessage: originalSendMessage,
    showSources,
    toggleSources,
    loadChatHistory,
    clearChatHistory
  } = useChatStream(sessionId);

  const setInputMessage = originalSetInputMessage;

  const sendMessage = originalSendMessage;

  useEffect(() => {
    // Tạo session mới khi component mount nếu chưa có
    const createNewSession = async () => {
      if (!sessionId) {
        try {
          const response = await axios.post(`${API_BASE_URL}/chat/session`);
          const newSessionId = response.data.session_id;
          setSessionId(newSessionId);
          localStorage.setItem('chatSessionId', newSessionId);
        } catch (error) {
          console.error('Error creating session:', error);
          // Fallback: tạo session ID local nếu backend không có
          const fallbackSessionId = `session_${Date.now()}`;
          setSessionId(fallbackSessionId);
          localStorage.setItem('chatSessionId', fallbackSessionId);
        }
      }
    };
    createNewSession();
  }, [sessionId]);

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const createNewSession = async () => {
    try {
      const response = await axios.post(`${API_BASE_URL}/chat/session`);
      const newSessionId = response.data.session_id;
      setSessionId(newSessionId);
      localStorage.setItem('chatSessionId', newSessionId);
      setMessages([]); // Clear messages for new session
    } catch (error) {
      console.error('Error creating new session:', error);
      // Fallback: tạo session ID local nếu backend không có
      const fallbackSessionId = `session_${Date.now()}`;
      setSessionId(fallbackSessionId);
      localStorage.setItem('chatSessionId', fallbackSessionId);
      setMessages([]); // Clear messages for new session
    }
  };

  const handleChatMessage = (message) => {
    // Add bot message to chat
    const botMessage = {
      id: Date.now(),
      type: 'bot',
      content: message,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, botMessage]);
  };

  const openCT01Modal = () => {
    setIsCT01ModalOpen(true);
  };

  const closeCT01Modal = () => {
    setIsCT01ModalOpen(false);
  };

  const openVoiceChat = () => {
    navigate('/voice-call');
  };

  // Check for CT01 related messages and open modal
  useEffect(() => {
    const lastMessage = messages[messages.length - 1];
    if (lastMessage && lastMessage.type === 'user') {
      const content = lastMessage.content.toLowerCase();
      
      // Kiểm tra nhiều pattern khác nhau
      if (content.includes('ct01') || 
          content.includes('điền') || 
          content.includes('biểu mẫu') ||
          content.includes('tờ khai') ||
          content.includes('thuế')) {
        // Add a small delay to let the user see the response first
        setTimeout(() => {
          openCT01Modal();
        }, 1000);
      }
    }
  }, [messages]);

  return (
    <Routes>
      <Route path="/" element={
        <div className="min-h-screen bg-white">
          {/* CT01 Test Page Content */}
          <CT01TestPage />
          
          {/* Floating Chatbot */}
          <FloatingChatbot
            key="floating-chatbot-fixed" // FIXED KEY TO PREVENT RE-MOUNTING
            messages={messages}
            onSend={sendMessage}
            isLoading={isLoading}
            sessionId={sessionId}
            showSources={showSources}
            toggleSources={toggleSources}
            inputMessage={inputMessage}
            setInputMessage={setInputMessage}
            handleKeyPress={handleKeyPress}
            loadChatHistory={loadChatHistory}
            clearChatHistory={clearChatHistory}
            createNewSession={createNewSession}
            openCT01Modal={openCT01Modal}
            openVoiceChat={openVoiceChat}
          />

          {/* CT01 Modal */}
          <CT01Modal
            isOpen={isCT01ModalOpen}
            onClose={closeCT01Modal}
            onChatMessage={handleChatMessage}
          />
        </div>
      } />
      <Route path="/voice-call" element={<VoiceCallPage />} />
    </Routes>
  );
}

export default App; 