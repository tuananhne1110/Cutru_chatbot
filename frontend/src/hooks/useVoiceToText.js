import { useState, useRef, useCallback } from 'react';

const API_BASE = 'http://localhost:8000';

const useVoiceToText = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [voiceLoading, setVoiceLoading] = useState(false);
  const [voiceError, setVoiceError] = useState(null);
  const [voiceText, setVoiceText] = useState('');
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);

  const startRecording = useCallback(async () => {
    try {
      setVoiceError(null);
      setVoiceLoading(true);
      
      // Get microphone access
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true
        } 
      });
      
      // Start recording with backend API
      const response = await fetch(`${API_BASE}/voice/start-recording`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      if (data.status !== 'success') {
        throw new Error(data.message || 'Failed to start recording');
      }
      
      // Create MediaRecorder
      mediaRecorderRef.current = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });
      
      chunksRef.current = [];
      
      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };
      
      mediaRecorderRef.current.onstop = async () => {
        const audioBlob = new Blob(chunksRef.current, { type: 'audio/webm;codecs=opus' });
        await processAudio(audioBlob);
        
        // Stop tracks
        stream.getTracks().forEach(track => track.stop());
      };
      
      mediaRecorderRef.current.start(1000); // Collect data every 1 second
      setIsRecording(true);
      setVoiceLoading(false);
      
    } catch (error) {
      console.error('Error starting recording:', error);
      setVoiceError(error.message);
      setVoiceLoading(false);
      setIsRecording(false);
    }
  }, []);

  const stopRecording = useCallback(async () => {
    try {
      if (mediaRecorderRef.current && isRecording) {
        mediaRecorderRef.current.stop();
        setIsRecording(false);
        setVoiceLoading(true);
        
        // Stop recording on backend
        await fetch(`${API_BASE}/voice/stop-recording`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          }
        });
      }
    } catch (error) {
      console.error('Error stopping recording:', error);
      setVoiceError(error.message);
      setVoiceLoading(false);
    }
  }, [isRecording]);

  const processAudio = async (audioBlob) => {
    try {
      setVoiceLoading(true);
      
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
      
      if (data.text && data.text.trim()) {
        setVoiceText(data.text.trim());
        setVoiceError(null);
      } else {
        setVoiceError('Không nhận được text từ audio');
      }
      
    } catch (error) {
      console.error('Error processing audio:', error);
      setVoiceError(error.message);
    } finally {
      setVoiceLoading(false);
    }
  };

  const toggleRecording = useCallback(() => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  }, [isRecording, startRecording, stopRecording]);

  const clearVoiceText = useCallback(() => {
    setVoiceText('');
    setVoiceError(null);
  }, []);

  return {
    isRecording,
    voiceLoading,
    voiceError,
    voiceText,
    startRecording,
    stopRecording,
    toggleRecording,
    clearVoiceText
  };
};

export default useVoiceToText;
