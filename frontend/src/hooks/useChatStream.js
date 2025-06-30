import { useState } from 'react';

export default function useChatStream(sessionId) {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showSources, setShowSources] = useState({});

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
      const response = await fetch(`/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: userMessage.content, session_id: sessionId })
      });
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let result = '';
      let done = false;
      while (!done) {
        const { value, done: doneReading } = await reader.read();
        done = doneReading;
        if (value) {
          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');
          let newContent = result;
          for (let line of lines) {
            line = line.trim();
            if (!line) continue;
            if (line.startsWith('data:')) line = line.replace('data:', '').trim();
            try {
              const data = JSON.parse(line);
              const content = data?.choices?.[0]?.delta?.content;
              if (typeof content === 'string' && content.length > 0) {
                newContent += content;
              }
            } catch (e) {
              // Không làm gì nếu không phải JSON hợp lệ
            }
          }
          if (newContent !== result) {
            result = newContent;
            setMessages(prev => prev.map(msg =>
              msg.id === botMessageId ? { ...msg, content: result } : msg
            ));
          }
        }
      }
    } catch (error) {
      setMessages(prev => [...prev, {
        id: Date.now() + 2,
        type: 'error',
        content: 'Xin lỗi, có lỗi xảy ra. Vui lòng thử lại.',
        timestamp: new Date().toISOString()
      }]);
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
    toggleSources
  };
} 