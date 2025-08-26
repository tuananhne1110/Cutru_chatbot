import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import './VoiceCallPage.css';

const VoiceCallPage = () => {
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [isListening, setIsListening] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentTranscript, setCurrentTranscript] = useState('');
  const [isPlaying, setIsPlaying] = useState(false);
  const [callDuration, setCallDuration] = useState(0);
  const [callStartTime] = useState(Date.now());
  const messagesEndRef = useRef(null);
  const intervalRef = useRef(null);
  const API_BASE = (process.env.REACT_APP_API_BASE || '').trim() || `${window.location.protocol}//${window.location.hostname}:8000`;

  // Format time as MM:SS
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Timer effect
  useEffect(() => {
    intervalRef.current = setInterval(() => {
      const elapsed = Math.floor((Date.now() - callStartTime) / 1000);
      setCallDuration(elapsed);
    }, 1000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [callStartTime]);

  // Auto scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Initialize with AI greeting
  useEffect(() => {
    const initMessage = {
      id: Date.now(),
      type: 'ai',
      content: 'Chào ông bà, tôi là Nhân viên AI Trung tâm Phục vụ hành chính công Hà Nội. Vui lòng nói hoặc bấm:\nSố 1 để hỏi đáp thủ tục hành chính hoặc phản ánh kiến nghị\nSố 2 để tra cứu hồ sơ',
      timestamp: new Date().toLocaleTimeString('vi-VN', { 
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        fractionalSecondDigits: 3
      })
    };
    setMessages([initMessage]);

    // Auto-play greeting
    setTimeout(() => {
      speakText(initMessage.content);
    }, 1000);
  }, []);

  const startListening = async () => {
    try {
      setIsListening(true);
      setCurrentTranscript('');
      
      const response = await fetch(`${API_BASE}/voice/start-recording`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (!response.ok) {
        throw new Error('Failed to start recording');
      }

      // Poll for transcript updates
      const pollInterval = setInterval(async () => {
        try {
          const textResponse = await fetch(`${API_BASE}/voice/get-current-text`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
          });
          
          if (textResponse.ok) {
            const data = await textResponse.json();
            setCurrentTranscript(data.text || '');
          }
        } catch (error) {
          console.error('Error polling transcript:', error);
        }
      }, 500);

      window.voicePollingInterval = pollInterval;

    } catch (error) {
      console.error('Error starting voice recording:', error);
      setIsListening(false);
    }
  };

  const stopListening = async () => {
    try {
      if (window.voicePollingInterval) {
        clearInterval(window.voicePollingInterval);
        window.voicePollingInterval = null;
      }

      setIsListening(false);
      setIsProcessing(true);

      const response = await fetch(`${API_BASE}/voice/stop-recording`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      if (!response.ok) {
        throw new Error('Failed to stop recording');
      }

      const data = await response.json();
      const finalText = data.text?.trim() || currentTranscript.trim();

      if (finalText) {
        // Add user message
        const userMessage = {
          id: Date.now(),
          type: 'user',
          content: finalText,
          timestamp: new Date().toLocaleTimeString('vi-VN', { 
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            fractionalSecondDigits: 3
          }),
          confidence: '97%/50%' // Simulate confidence scores
        };
        setMessages(prev => [...prev, userMessage]);
        setCurrentTranscript('');

        // Process through chat pipeline
        await processChatResponse(finalText);
      }

    } catch (error) {
      console.error('Error stopping voice recording:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  const processChatResponse = async (question) => {
    try {
      const botMessageId = Date.now() + 1;
      
      // Add empty AI message
      setMessages(prev => [...prev, {
        id: botMessageId,
        type: 'ai',
        content: '',
        timestamp: new Date().toLocaleTimeString('vi-VN', { 
          hour12: false,
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          fractionalSecondDigits: 3
        })
      }]);

      // Stream response from chat API
      const response = await fetch(`${API_BASE}/chat/stream`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json; charset=utf-8',
          'Accept-Charset': 'utf-8'
        },
        body: JSON.stringify({
          question: question,
          session_id: `voice_call_${Date.now()}`,
          messages: []
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
        const readResult = await reader.read();
        const value = readResult.value;
        const doneReading = readResult.done;
        done = doneReading;
        
        if (value) {
          buffer += decoder.decode(value, { stream: !done });
          const linesArr = buffer.split(/\n\n/);
          buffer = linesArr.pop() || '';
          
          for (let idx = 0; idx < linesArr.length; idx++) {
            let line = linesArr[idx];
            line = line.trim();
            if (line.startsWith('data:')) {
              const jsonStr = line.replace(/^data:\s*/, '');
              try {
                const obj = JSON.parse(jsonStr);
                if (obj.type === 'chunk' && obj.content) {
                  result += obj.content;
                  
                  // Update AI message
                  setMessages(prev => {
                    const updated = [...prev];
                    const aiIdx = updated.findIndex(msg => msg.id === botMessageId);
                    if (aiIdx !== -1) {
                      updated[aiIdx] = { ...updated[aiIdx], content: result };
                    }
                    return updated;
                  });
                }
              } catch (e) {
                // Ignore parse errors
              }
            }
          }
        }
      }

      // After streaming completes, use TTS to speak the response
      if (result.trim()) {
        await speakText(result.trim());
      }

    } catch (error) {
      console.error('Error processing chat response:', error);
      const errorMessage = {
        id: Date.now(),
        type: 'ai',
        content: 'Xin lỗi, có lỗi xảy ra. Vui lòng thử lại.',
        timestamp: new Date().toLocaleTimeString('vi-VN', { 
          hour12: false,
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          fractionalSecondDigits: 3
        })
      };
      setMessages(prev => [...prev, errorMessage]);
    }
  };

  const speakText = async (text) => {
    try {
      setIsPlaying(true);
      
      const response = await fetch(`${API_BASE}/voice/tts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });

      if (!response.ok) {
        throw new Error(`TTS failed: ${response.status}`);
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      
      audio.onended = () => {
        setIsPlaying(false);
        URL.revokeObjectURL(url);
      };
      
      audio.onerror = () => {
        setIsPlaying(false);
        URL.revokeObjectURL(url);
      };

      await audio.play();
      
    } catch (error) {
      console.error('Error speaking text:', error);
      setIsPlaying(false);
    }
  };

  const endCall = () => {
    // Clean up any ongoing processes
    if (window.voicePollingInterval) {
      clearInterval(window.voicePollingInterval);
    }
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }
    
    // Navigate back to main page
    navigate('/');
  };

  return (
    <div className="voice-call-page">
      {/* Header */}
      <div className="call-header">
        <button className="back-button" onClick={endCall}>
          ‹
        </button>
        <h1 className="call-title">Tổng đài hỗ trợ dịch vụ công</h1>
      </div>

      {/* Call Controls */}
      <div className="call-controls">
        <div className="call-timer">
          🔴 {formatTime(callDuration)}
        </div>
        <button className="stop-call-button" onClick={endCall}>
          🔇 STOP CALL
        </button>
      </div>

      {/* Messages */}
      <div className="call-messages">
        {messages.map((message) => (
          <div key={message.id} className={`call-message ${message.type}`}>
            <div className="message-header">
              <div className="message-avatar">
                {message.type === 'ai' ? '🏛️' : '👤'}
              </div>
              <div className="message-info">
                <div className="message-timestamp">
                  [{message.timestamp}]
                </div>
                {message.confidence && (
                  <div className="message-confidence">
                    🎤: {message.confidence}
                  </div>
                )}
              </div>
            </div>
            <div className="message-content">
              {message.content}
            </div>
          </div>
        ))}
        
        {/* Current transcript while listening */}
        {(isListening || currentTranscript) && (
          <div className="call-message user active">
            <div className="message-header">
              <div className="message-avatar">👤</div>
              <div className="message-info">
                <div className="message-timestamp">
                  [{new Date().toLocaleTimeString('vi-VN', { 
                    hour12: false,
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit',
                    fractionalSecondDigits: 3
                  })}]
                </div>
                <div className="message-confidence">
                  🎤: {isListening ? 'listening...' : ''}
                </div>
              </div>
            </div>
            <div className="message-content">
              {currentTranscript || "🎤 Đang nghe..."}
            </div>
          </div>
        )}
        
        {/* Processing indicator */}
        {isProcessing && (
          <div className="call-message ai processing">
            <div className="message-header">
              <div className="message-avatar">🏛️</div>
              <div className="message-info">
                <div className="message-timestamp">
                  [{new Date().toLocaleTimeString('vi-VN', { 
                    hour12: false,
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit',
                    fractionalSecondDigits: 3
                  })}]
                </div>
              </div>
            </div>
            <div className="message-content processing">
              <span className="thinking-dots">
                <span></span>
                <span></span>
                <span></span>
              </span>
              Đang xử lý...
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Voice Control */}
      <div className="voice-control">
        <div className="control-status">
          {isListening && (
            <div className="status-text listening">
              🎤 Đang ghi âm - Nhả để gửi
            </div>
          )}
          {isProcessing && (
            <div className="status-text processing">
              ⏳ Đang xử lý câu hỏi...
            </div>
          )}
          {isPlaying && (
            <div className="status-text playing">
              🔊 AI đang trả lời...
            </div>
          )}
          {!isListening && !isProcessing && !isPlaying && (
            <div className="status-text ready">
              Nhấn và giữ mic để nói chuyện
            </div>
          )}
        </div>
        
        <div className="voice-button-container">
          <button
            className={`voice-control-button ${isListening ? 'recording' : ''}`}
            onMouseDown={startListening}
            onMouseUp={stopListening}
            onTouchStart={startListening}
            onTouchEnd={stopListening}
            disabled={isProcessing || isPlaying}
          >
            {isListening ? '🔴' : '🎤'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default VoiceCallPage;
