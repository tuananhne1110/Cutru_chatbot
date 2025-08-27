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
  const [autoModeAvailable, setAutoModeAvailable] = useState(false);
  const [voiceStatus, setVoiceStatus] = useState('');
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

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      // Cleanup on component unmount
      if (window.voicePollingInterval) {
        clearInterval(window.voicePollingInterval);
      }
      if (window.autoVoiceWS) {
        window.autoVoiceWS.close();
        window.autoVoiceWS = null;
      }
    };
  }, []);

  // Check if auto voice mode is available
  useEffect(() => {
    const checkAutoMode = async () => {
      try {
        const response = await fetch(`${API_BASE}/chat/voice/info`);
        const data = await response.json();
        if (data.enhanced_available && data.auto_voice_endpoint) {
          setAutoModeAvailable(true);
          console.log('🎤✅ Auto voice mode available');
          // Auto connect to WebSocket when available
          setTimeout(connectToAutoVoiceWebSocket, 1000);
        }
      } catch (error) {
        console.log('🎤ℹ️ Auto voice mode not available, using fallback mode');
        setVoiceStatus('Chế độ cơ bản - Nhấn và giữ để nói');
      }
    };
    
    checkAutoMode();
  }, [API_BASE]);

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
    if (autoModeAvailable) {
      startAutoListening();
    } else {
      // Fallback to old API if auto mode not available
      startManualListening();
    }
  };

  const startManualListening = async () => {
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

  const connectToAutoVoiceWebSocket = () => {
    try {
      setVoiceStatus('Đang kết nối...');
      const wsUrl = `${API_BASE.replace('http', 'ws')}/chat/auto-voice`;
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        console.log('🎤🤖 Connected to auto voice WebSocket');
        setVoiceStatus('Sẵn sàng - Click để bắt đầu nói!');
        window.autoVoiceWS = ws;
      };
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleAutoVoiceMessage(data);
        } catch (error) {
          console.error('Auto voice message error:', error);
        }
      };
      
      ws.onerror = (error) => {
        console.error('Auto voice WebSocket error:', error);
        setVoiceStatus('Lỗi kết nối');
      };
      
      ws.onclose = () => {
        console.log('🎤🤖 Auto voice WebSocket disconnected');
        setIsListening(false);
        setIsProcessing(false);
        setVoiceStatus('Đã ngắt kết nối');
        window.autoVoiceWS = null;
      };
      
    } catch (error) {
      console.error('Error connecting to auto voice WebSocket:', error);
      setVoiceStatus('Lỗi kết nối');
    }
  };
  
  const handleAutoVoiceMessage = (data) => {
    switch (data.type) {
      case 'ready':
        setVoiceStatus(data.message);
        break;
        
      case 'listening_started':
        setIsListening(true);
        setVoiceStatus('🎤 Đang nghe... (tự động phát hiện kết thúc)');
        setCurrentTranscript('');
        break;
        
      case 'speech_started':
        setVoiceStatus('🗣️ Phát hiện giọng nói...');
        break;
        
      case 'partial_transcription':
        setCurrentTranscript(data.text);
        break;
        
      case 'speech_ended':
        setVoiceStatus('⏳ Đang xử lý...');
        break;
        
      case 'silence_detected':
        setVoiceStatus('🤫 Phát hiện im lặng - đang kết thúc...');
        break;
        
      case 'final_transcription':
        setCurrentTranscript(data.text);
        const userMessage = {
          id: Date.now(),
          type: 'user',
          content: data.text,
          timestamp: new Date().toLocaleTimeString('vi-VN', { hour12: false })
        };
        setMessages(prev => [...prev, userMessage]);
        setIsListening(false);
        setIsProcessing(true);
        setVoiceStatus('🤖 Đang suy nghĩ...');
        break;
        
      case 'processing_started':
        setIsProcessing(true);
        setVoiceStatus('🔄 Đang xử lý câu hỏi...');
        break;
        
      case 'response_start':
        setVoiceStatus('📝 Đang tạo câu trả lời...');
        break;
        
      case 'response_chunk':
        // Update the AI message progressively
        setMessages(prev => {
          const newMessages = [...prev];
          const lastMessage = newMessages[newMessages.length - 1];
          
          if (lastMessage && lastMessage.type === 'ai' && lastMessage.isStreaming) {
            lastMessage.content += data.text;
          } else {
            newMessages.push({
              id: Date.now(),
              type: 'ai',
              content: data.text,
              timestamp: new Date().toLocaleTimeString('vi-VN', { hour12: false }),
              isStreaming: true
            });
          }
          return newMessages;
        });
        break;
        
      case 'tts_start':
        setVoiceStatus('🔊 Đang tạo âm thanh...');
        break;
        
      case 'response_complete':
        setMessages(prev => {
          const newMessages = [...prev];
          const lastMessage = newMessages[newMessages.length - 1];
          if (lastMessage && lastMessage.isStreaming) {
            lastMessage.isStreaming = false;
          }
          return newMessages;
        });
        setIsProcessing(false);
        setVoiceStatus('✅ Hoàn thành - Click để nói tiếp!');
        break;
        
      case 'error':
        console.error('Auto voice error:', data.message);
        setVoiceStatus(`❌ Lỗi: ${data.message}`);
        setIsListening(false);
        setIsProcessing(false);
        break;
        
      default:
        console.log('Unknown auto voice message:', data);
    }
  };
  
  const startAutoListening = () => {
    if (window.autoVoiceWS && window.autoVoiceWS.readyState === WebSocket.OPEN) {
      window.autoVoiceWS.send(JSON.stringify({ type: 'start_listening' }));
    } else {
      console.error('Auto voice WebSocket not connected');
      connectToAutoVoiceWebSocket();
    }
  };

  const stopListening = async () => {
    // Only used for fallback manual mode
    if (autoModeAvailable) {
      // In auto mode, stopping is handled automatically
      return;
    }
    
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
    
    // Close auto voice WebSocket if connected
    if (window.autoVoiceWS) {
      window.autoVoiceWS.close();
      window.autoVoiceWS = null;
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
          {/* Auto mode indicator */}
          {autoModeAvailable && (
            <div className="auto-mode-indicator">
              <span className="auto-mode-enabled">
                🤖 SMART VOICE: {voiceStatus || 'Sẵn sàng'}
              </span>
            </div>
          )}
          
          {/* Status messages */}
          {autoModeAvailable ? (
            <div className="status-text auto">
              {voiceStatus || 'Sẵn sàng - Click để bắt đầu nói!'}
            </div>
          ) : (
            <div className="status-text fallback">
              📱 Chế độ cơ bản - Nhấn và giữ để nói
            </div>
          )}
        </div>
        
        <div className="voice-button-container">
          {/* Voice control button */}
          <button
            className={`voice-control-button ${isListening ? 'recording' : ''} ${autoModeAvailable ? 'auto-mode' : ''}`}
            onClick={autoModeAvailable ? startAutoListening : undefined}
            onMouseDown={autoModeAvailable ? undefined : startListening}
            onMouseUp={autoModeAvailable ? undefined : stopListening}
            onTouchStart={autoModeAvailable ? undefined : startListening}
            onTouchEnd={autoModeAvailable ? undefined : stopListening}
            disabled={isProcessing || isPlaying}
          >
            {autoModeAvailable ? (
              isListening ? '🔴 Nghe...' : '🎤 Nói'
            ) : (
              isListening ? '🔴' : '🎤'
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default VoiceCallPage;
