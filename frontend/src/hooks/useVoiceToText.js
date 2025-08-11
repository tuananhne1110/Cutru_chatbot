import { useState, useCallback, useEffect } from 'react';
import voiceToTextService from '../services/voiceToTextService';
import browserVoiceService from '../services/browserVoiceService';

const useVoiceToText = (onTextReceived) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [currentText, setCurrentText] = useState('');

  const startRecording = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      setCurrentText('');
      
      // Use server-side voice recognition (PhoWhisper model)
      await voiceToTextService.startRecording();
      setIsRecording(true);
      
      // Start polling for text updates
      voiceToTextService.startPolling(
        (text) => {
          setCurrentText(text);
          // Stream text directly to input field
          if (text && text.trim()) {
            onTextReceived(text);
          }
        },
        (error) => {
          setError('Failed to get text updates');
          setIsRecording(false);
        },
        1000 // Poll every second
      );
      
      setIsLoading(false);
      
    } catch (error) {
      setError(error.message);
      setIsRecording(false);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const stopRecording = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      // Stop server-side voice recognition
      voiceToTextService.stopPolling();
      
      const result = await voiceToTextService.stopRecording();
      setIsRecording(false);
      
      if (result.text && result.text.trim()) {
        onTextReceived(result.text.trim());
      }
      
      setCurrentText('');
      
    } catch (error) {
      setError(error.message);
      setIsRecording(false);
    } finally {
      setIsLoading(false);
    }
  }, [onTextReceived]);

  const toggleRecording = useCallback(() => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  }, [isRecording, startRecording, stopRecording]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (isRecording) {
        voiceToTextService.stopPolling();
      }
    };
  }, [isRecording]);

  return {
    isRecording,
    isLoading,
    error,
    currentText,
    startRecording,
    stopRecording,
    toggleRecording
  };
};

export default useVoiceToText;
