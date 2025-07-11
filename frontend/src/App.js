import React, { useEffect, useState } from 'react';
import FloatingChatbot from './components/FloatingChatbot';
import DemoPage from './components/DemoPage';
import useChatStream from './hooks/useChatStream';
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  const [sessionId, setSessionId] = useState(() => {
    // Kiểm tra localStorage trước
    const savedSessionId = localStorage.getItem('chatSessionId');
    return savedSessionId || null;
  });
  
  const {
    messages,
    setMessages,
    inputMessage,
    setInputMessage,
    isLoading,
    sendMessage,
    showSources,
    toggleSources,
    loadChatHistory,
    clearChatHistory
  } = useChatStream(sessionId);

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
    }
  };

  return (
    <div className="min-h-screen bg-white">
      {/* Demo Page Content */}
      <DemoPage />
      
      {/* Floating Chatbot */}
      <FloatingChatbot
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
      />
    </div>
  );
}

export default App; 