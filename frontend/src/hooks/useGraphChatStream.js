
// frontend/src/hooks/useGraphChatStream.js
import { useState, useEffect, useCallback } from 'react';

export default function useGraphChatStream(sessionId, confirmDialog = window.confirm) {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showSources, setShowSources] = useState({});
  const [ragType, setRagType] = useState('hybrid'); // 'vector', 'graph', 'hybrid'

  const sendMessage = async (useGraphRAG = true) => {
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
      const endpoint = useGraphRAG ? '/chat/graph/stream' : '/chat/stream';
      
      const response = await fetch(`${API_URL}${endpoint}`, {
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
      let buffer = '';
      
      while (!done) {
        const { value, done: doneReading } = await reader.read();
        done = doneReading;
        
        if (value) {
          buffer += decoder.decode(value, { stream: !done });
          let lines = buffer.split(/\n\n/);
          buffer = lines.pop() || '';
          
          for (let line of lines) {
            line = line.trim();
            if (line.startsWith('data:')) {
              const jsonStr = line.replace(/^data:\s*/, '');
              try {
                const obj = JSON.parse(jsonStr);
                
                if (obj.type === 'chunk' && obj.content) {
                  const newResult = result + obj.content;
                  result = newResult;
                  setMessages(prev => {
                    const idx = prev.findIndex(msg => msg.id === botMessageId);
                    if (idx !== -1) {
                      const updated = [...prev];
                      updated[idx] = { ...updated[idx], content: newResult };
                      return updated;
                    }
                    return prev;
                  });
                }
                
                if (obj.type === 'metadata') {
                  // Handle Graph RAG metadata
                  setMessages(prev => {
                    const newMessages = [...prev];
                    for (let i = newMessages.length - 1; i >= 0; i--) {
                      if (newMessages[i].type === 'bot') {
                        newMessages[i].metadata = obj.metadata;
                        if (obj.metadata.rag_type) {
                          setRagType(obj.metadata.rag_type);
                        }
                        break;
                      }
                    }
                    return newMessages;
                  });
                }
                
                if (obj.type === 'sources') {
                  setMessages(prev => {
                    const newMessages = [...prev];
                    for (let i = newMessages.length - 1; i >= 0; i--) {
                      if (newMessages[i].type === 'bot') {
                        newMessages[i].sources = obj.sources;
                        break;
                      }
                    }
                    return newMessages;
                  });
                }
              } catch (e) {
                // Ignore parse errors
              }
            }
          }
        }
      }
    } catch (error) {
      console.error('Error in graph chat stream:', error);
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

  const toggleSources = (messageId) => {
    setShowSources(prev => ({ ...prev, [messageId]: !prev[messageId] }));
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
    ragType
  };
}