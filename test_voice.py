#!/usr/bin/env python3
"""
Script test đơn giản cho voice-to-text
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_voice_recognition():
    """Test voice recognition functionality"""
    try:
        print("Testing voice recognition...")
        
        # Import và test SpeechRecognizer
        from stream_speech import SpeechRecognizer
        
        print("✓ SpeechRecognizer imported successfully")
        
        # Test initialization
        recognizer = SpeechRecognizer(
            batch_size=4,
            num_workers=1
        )
        print("✓ SpeechRecognizer initialized successfully")
        
        # Test basic functionality
        current_text = recognizer.get_current_text()
        print(f"✓ Current text: '{current_text}'")
        
        # Cleanup
        recognizer.stop()
        print("✓ Cleanup completed")
        
        print("\n🎉 Voice recognition test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Voice recognition test failed: {e}")
        return False

def test_audio_devices():
    """Test audio device availability"""
    try:
        import sounddevice as sd
        
        print("\nTesting audio devices...")
        
        # List available devices
        devices = sd.query_devices()
        print(f"✓ Found {len(devices)} audio devices")
        
        # Find input devices
        input_devices = [d for d in devices if d['max_inputs'] > 0]
        print(f"✓ Found {len(input_devices)} input devices")
        
        for i, device in enumerate(input_devices):
            print(f"  {i}: {device['name']} (channels: {device['max_inputs']})")
        
        # Test default device
        default_device = sd.query_devices(kind='input')
        print(f"✓ Default input device: {default_device['name']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Audio device test failed: {e}")
        return False

if __name__ == "__main__":
    print("🔊 Voice-to-Text Test Suite")
    print("=" * 40)
    
    # Test audio devices first
    audio_ok = test_audio_devices()
    
    if audio_ok:
        # Test voice recognition
        voice_ok = test_voice_recognition()
        
        if voice_ok:
            print("\n✅ All tests passed! Voice-to-text is ready to use.")
        else:
            print("\n❌ Voice recognition test failed. Check dependencies.")
    else:
        print("\n❌ Audio device test failed. Check microphone setup.")
