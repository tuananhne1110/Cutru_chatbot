const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class VoiceToTextService {
  constructor() {
    this.isRecording = false;
    this.websocket = null;
  }

  async startRecording() {
    try {
      const response = await fetch(`${API_BASE_URL}/voice/start-recording`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to start recording');
      }

      this.isRecording = true;
      return await response.json();
    } catch (error) {
      console.error('Error starting recording:', error);
      throw error;
    }
  }

  async stopRecording() {
    try {
      const response = await fetch(`${API_BASE_URL}/voice/stop-recording`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error('Failed to stop recording');
      }

      this.isRecording = false;
      return await response.json();
    } catch (error) {
      console.error('Error stopping recording:', error);
      throw error;
    }
  }

  async getStatus() {
    try {
      const response = await fetch(`${API_BASE_URL}/voice/status`);
      if (!response.ok) {
        throw new Error('Failed to get status');
      }
      return await response.json();
    } catch (error) {
      console.error('Error getting status:', error);
      throw error;
    }
  }

  async getCurrentText() {
    try {
      const response = await fetch(`${API_BASE_URL}/voice/get-current-text`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      if (!response.ok) {
        throw new Error('Failed to get current text');
      }
      return await response.json();
    } catch (error) {
      console.error('Error getting current text:', error);
      throw error;
    }
  }

  startPolling(onTextUpdate, onError, interval = 1000) {
    this.pollingInterval = setInterval(async () => {
      try {
        if (this.isRecording) {
          const result = await this.getCurrentText();
          if (result.text) {
            onTextUpdate(result.text);
          }
        }
      } catch (error) {
        onError(error);
      }
    }, interval);
  }

  stopPolling() {
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
      this.pollingInterval = null;
    }
  }

  isCurrentlyRecording() {
    return this.isRecording;
  }
}

export default new VoiceToTextService();
