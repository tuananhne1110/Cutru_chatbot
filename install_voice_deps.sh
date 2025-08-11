#!/bin/bash

echo "Installing voice-to-text dependencies..."

# Update package list
sudo apt-get update

# Install system dependencies for audio processing
sudo apt-get install -y \
    portaudio19-dev \
    python3-pyaudio \
    libasound2-dev \
    libportaudio2 \
    libportaudiocpp0 \
    ffmpeg

# Install Python dependencies
pip install sounddevice==0.4.6
pip install webrtcvad==2.0.10


echo "Voice-to-text dependencies installed successfully!"
echo ""
echo "Note: If you encounter any issues with audio devices, you may need to:"
echo "1. Check your microphone permissions"
echo "2. Install additional audio drivers if needed"
echo "3. Configure your audio input device"
