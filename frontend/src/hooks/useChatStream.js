import { useState, useEffect, useCallback } from 'react';

export default function useChatStream(sessionId, confirmDialog = window.confirm) {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showSources, setShowSources] = useState({});

  const loadChatHistory = useCallback(async () => {
    if (!sessionId) return;
    try {
      const response = await fetch(`/chat/history/${sessionId}`);
      if (response.ok) {
        const data = await response.json();
        const historyMessages = [];
        data.messages.forEach(msg => {
          historyMessages.push({
            id: `user_${msg.id || Date.now()}_${Math.random()}`,
            type: 'user',
            content: msg.question,
            timestamp: msg.created_at
          });
          historyMessages.push({
            id: `bot_${msg.id || Date.now()}_${Math.random()}`,
            type: 'bot',
            content: msg.answer,
            timestamp: msg.created_at,
            sources: msg.sources || []
          });
        });
        historyMessages.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
        setMessages(historyMessages);
      } else {
        console.error('Failed to load chat history:', response.status);
      }
    } catch (error) {
      console.error('Error loading chat history:', error);
    }
  }, [sessionId]);

  const clearChatHistory = async () => {
    if (!sessionId) return;
    
    if (!confirmDialog('Bạn có chắc chắn muốn xóa toàn bộ lịch sử chat?')) {
      return;
    }
    
    try {
      const response = await fetch(`/chat/history/${sessionId}`, {
        method: 'DELETE'
      });
      if (response.ok) {
        setMessages([]);
        alert('Đã xóa lịch sử chat thành công!');
      } else {
        alert('Có lỗi xảy ra khi xóa lịch sử chat!');
      }
    } catch (error) {
      console.error('Error clearing chat history:', error);
      alert('Có lỗi xảy ra khi xóa lịch sử chat!');
    }
  };

  const toggleSources = (messageId) => {
    setShowSources(prev => ({ ...prev, [messageId]: !prev[messageId] }));
  };

  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;
    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: inputMessage,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);
    const botMessageId = Date.now() + 1;
    setMessages(prev => [
      ...prev,
      { id: botMessageId, type: 'bot', content: '', timestamp: new Date().toISOString() }
    ]);
    try {
      const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      const response = await fetch(`${API_URL}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: inputMessage,
          session_id: sessionId,
          messages: [
            ...messages.map(m => ({
              role: m.type === 'user' ? 'user' : 'assistant',
              content: m.content
            })),
            { role: 'user', content: inputMessage }
          ]
        })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let result = '';
      let done = false;
      
      while (!done) {
        const { value, done: doneReading } = await reader.read();
        done = doneReading;
        if (value) {
          const chunk = decoder.decode(value);
          if (chunk) {
            result += chunk;
            setMessages(prev => prev.map(msg =>
              msg.id === botMessageId ? { ...msg, content: result } : msg
            ));
          }
        }
      }
    } catch (error) {
      console.error('Error in chat stream:', error);
      setMessages(prev => prev.map(msg =>
        msg.id === botMessageId ? { 
          ...msg, 
        content: 'Xin lỗi, có lỗi xảy ra. Vui lòng thử lại.',
          type: 'error'
        } : msg
      ));
    } finally {
      setIsLoading(false);
    }
  };

  return {
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
  };
} 