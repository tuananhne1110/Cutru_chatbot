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
  const [useAutoMode, setUseAutoMode] = useState(true);
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

  // Enable auto voice mode 
  useEffect(() => {
    setAutoModeAvailable(true);
    setVoiceStatus('Sẵn sàng - Click để bắt đầu nói');
    console.log('🎤🔧 Using auto voice mode with turn detection');
  }, []);

  // Initialize with AI greeting
  useEffect(() => {
    const initMessage = {
      id: Date.now(),
      type: 'ai',
      content: 'Chào ông bà, tôi là Nhân viên AI Trung tâm Phục vụ hành chính công Hà Nội.',
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
    if (autoModeAvailable && useAutoMode) {
      console.log('🎤🚀 Starting auto voice mode');
      startAutoListening();
    } else {
      console.log('🎤📱 Fallback to manual mode');
      startManualListening();
    }
  };

  const startManualListening = async () => {
    try {
      setIsListening(true);
      setCurrentTranscript('');
      
      // Start backend recording session
      const response = await fetch(`${API_BASE}/voice/start-recording`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (!response.ok) {
        throw new Error('Failed to start recording');
      }

      // Get microphone access for actual recording
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true
        } 
      });
      
      // Create MediaRecorder
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });
      
      window.currentManualRecorder = mediaRecorder;
      window.currentManualStream = stream;
      const chunks = [];
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunks.push(event.data);
        }
      };
      
      mediaRecorder.onstop = async () => {
        // Process recorded audio
        if (chunks.length > 0) {
          const audioBlob = new Blob(chunks, { type: 'audio/webm;codecs=opus' });
          await processAudioBlob(audioBlob);
        }
        
        // Clean up
        stream.getTracks().forEach(track => track.stop());
        window.currentManualRecorder = null;
        window.currentManualStream = null;
      };
      
      // Start recording
      mediaRecorder.start();
      console.log('🎤 Started manual recording with MediaRecorder');

    } catch (error) {
      console.error('Error starting voice recording:', error);
      setIsListening(false);
      setVoiceStatus('Lỗi truy cập microphone');
    }
  };

  const processAudioBlob = async (audioBlob) => {
    try {
      setIsProcessing(true);
      setCurrentTranscript('');
      
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.webm');
      
      const response = await fetch(`${API_BASE}/voice/get-transcription`, {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      const finalText = data.text?.trim();
      
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
          confidence: '95%' // Simulate confidence
        };
        setMessages(prev => [...prev, userMessage]);
        
        // Process through chat pipeline
        await processChatResponse(finalText);
      } else {
        setVoiceStatus('Không nhận được text từ audio');
      }
      
    } catch (error) {
      console.error('Error processing audio blob:', error);
      setVoiceStatus('Lỗi xử lý audio');
    } finally {
      setIsProcessing(false);
    }
  };

  const connectToAutoVoiceWebSocket = () => {
    return new Promise((resolve, reject) => {
      try {
        // If already open, resolve immediately
        if (window.autoVoiceWS && window.autoVoiceWS.readyState === WebSocket.OPEN) {
          return resolve(window.autoVoiceWS);
        }
        setVoiceStatus('Đang kết nối...');
        const wsUrl = `${API_BASE.replace('http', 'ws')}/chat/auto-voice`;
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          console.log('🎤🤖 Connected to auto voice WebSocket');
          setVoiceStatus('Sẵn sàng - Click để bắt đầu nói!');
          window.autoVoiceWS = ws;
          resolve(ws);
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
        reject(error);
      }
    });
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
  
  const startAutoListening = async () => {
    try {
      // Ensure WebSocket is connected before starting
      if (!window.autoVoiceWS || window.autoVoiceWS.readyState !== WebSocket.OPEN) {
        console.log('🎤🔗 Connecting to auto voice WebSocket...');
        await connectToAutoVoiceWebSocket();
      }

      // Request microphone permission and start recording
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        } 
      });
      
      console.log('🎤🔴 Microphone access granted');
      setIsListening(true);
      
      // Create MediaRecorder for audio capture
      const options = { mimeType: 'audio/webm;codecs=opus' };
      const mediaRecorder = new MediaRecorder(stream, options);
      
      window.currentMediaRecorder = mediaRecorder;
      window.currentStream = stream;
      
      // Handle audio data
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0 && window.autoVoiceWS?.readyState === WebSocket.OPEN) {
          console.log('🎤📤 Sending audio chunk:', event.data.size, 'bytes');
          window.autoVoiceWS.send(event.data);
        }
      };
      
      mediaRecorder.onerror = (error) => {
        console.error('MediaRecorder error:', error);
        setVoiceStatus('Lỗi ghi âm');
      };
      
      mediaRecorder.onstop = () => {
        console.log('🎤⏹️ MediaRecorder stopped');
        setIsListening(false);
        if (window.currentStream) {
          window.currentStream.getTracks().forEach(track => track.stop());
          window.currentStream = null;
        }
      };
      
      // Send start command to backend first
      window.autoVoiceWS.send(JSON.stringify({ type: 'start_listening' }));

      // Start recording with larger chunks so backend processes them (>2000 bytes)
      mediaRecorder.start(750); // ~750ms chunks
      
    } catch (error) {
      console.error('Error starting auto listening:', error);
      setVoiceStatus('Lỗi truy cập microphone');
      setIsListening(false);
    }
  };

  const stopListening = async () => {
    try {
      setIsListening(false);
      
      // Stop manual MediaRecorder if active
      if (window.currentManualRecorder && window.currentManualRecorder.state === 'recording') {
        console.log('🎤⏹️ Stopping manual MediaRecorder');
        window.currentManualRecorder.stop();
      }

      // Stop backend recording session
      try {
        await fetch(`${API_BASE}/voice/stop-recording`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        });
      } catch (error) {
        console.error('Error stopping backend recording:', error);
      }

    } catch (error) {
      console.error('Error stopping voice recording:', error);
      setVoiceStatus('Lỗi dừng ghi âm');
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
    // Stop auto voice media recorder 
    if (window.currentMediaRecorder && window.currentMediaRecorder.state !== 'inactive') {
      window.currentMediaRecorder.stop();
    }
    if (window.currentStream) {
      window.currentStream.getTracks().forEach(track => track.stop());
      window.currentStream = null;
    }
    
    // Stop manual media recorder
    if (window.currentManualRecorder && window.currentManualRecorder.state !== 'inactive') {
      window.currentManualRecorder.stop();
    }
    if (window.currentManualStream) {
      window.currentManualStream.getTracks().forEach(track => track.stop());
      window.currentManualStream = null;
    }
    
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

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      // Stop auto voice media recorder
      if (window.currentMediaRecorder && window.currentMediaRecorder.state !== 'inactive') {
        window.currentMediaRecorder.stop();
      }
      if (window.currentStream) {
        window.currentStream.getTracks().forEach(track => track.stop());
        window.currentStream = null;
      }
      
      // Stop manual media recorder
      if (window.currentManualRecorder && window.currentManualRecorder.state !== 'inactive') {
        window.currentManualRecorder.stop();
      }
      if (window.currentManualStream) {
        window.currentManualStream.getTracks().forEach(track => track.stop());
        window.currentManualStream = null;
      }
      
      // Close WebSocket
      if (window.autoVoiceWS) {
        window.autoVoiceWS.close();
        window.autoVoiceWS = null;
      }
    };
  }, []);

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
        <div className="voice-button-container">
          {/* Voice control button */}
          <button
            className={`voice-control-button ${isListening ? 'recording' : ''} ${autoModeAvailable ? 'auto-mode' : ''}`}
            onClick={autoModeAvailable ? startListening : undefined}
            onMouseDown={autoModeAvailable ? undefined : startListening}
            onMouseUp={autoModeAvailable ? undefined : stopListening}
            onTouchStart={autoModeAvailable ? undefined : startListening}
            onTouchEnd={autoModeAvailable ? undefined : stopListening}
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
