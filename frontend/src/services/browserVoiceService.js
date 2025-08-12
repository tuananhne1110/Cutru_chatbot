class BrowserVoiceService {
  constructor() {
    this.recognition = null;
    this.isRecording = false;
    this.onTextUpdate = null;
    this.onError = null;
    this.onEnd = null;
    this.finalTranscript = '';
  }

  initialize() {
    // Check if browser supports speech recognition
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      throw new Error('Speech recognition not supported in this browser');
    }

    // Create speech recognition instance
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    this.recognition = new SpeechRecognition();

    // Configure recognition
    this.recognition.continuous = true;
    this.recognition.interimResults = true;
    this.recognition.lang = 'vi-VN'; // Vietnamese language

    // Set up event handlers
    this.recognition.onstart = () => {
      this.isRecording = true;
      console.log('Speech recognition started');
    };

    this.recognition.onresult = (event) => {
      let finalTranscript = '';
      let interimTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript;
        } else {
          interimTranscript += transcript;
        }
      }

      const currentText = finalTranscript || interimTranscript;
      if (this.onTextUpdate && currentText) {
        this.onTextUpdate(currentText);
      }
      
      // Store the final transcript for later use
      if (finalTranscript) {
        this.finalTranscript = finalTranscript;
      }
    };

    this.recognition.onerror = (event) => {
      console.error('Speech recognition error:', event.error);
      this.isRecording = false;
      if (this.onError) {
        this.onError(event.error);
      }
    };

    this.recognition.onend = () => {
      this.isRecording = false;
      console.log('Speech recognition ended');
      if (this.onEnd) {
        this.onEnd();
      }
    };
  }

  startRecording(onTextUpdate, onError, onEnd) {
    try {
      if (!this.recognition) {
        this.initialize();
      }

      this.onTextUpdate = onTextUpdate;
      this.onError = onError;
      this.onEnd = onEnd;
      this.finalTranscript = ''; // Reset final transcript

      this.recognition.start();
      return true;
    } catch (error) {
      console.error('Error starting speech recognition:', error);
      if (onError) {
        onError(error.message);
      }
      return false;
    }
  }

  stopRecording() {
    if (this.recognition && this.isRecording) {
      this.recognition.stop();
      this.isRecording = false;
    }
  }

  getFinalTranscript() {
    return this.finalTranscript;
  }

  isCurrentlyRecording() {
    return this.isRecording;
  }

  isSupported() {
    return 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;
  }
}

export default new BrowserVoiceService();
