#!/usr/bin/env python3
"""
Test script cho voice-to-text configuration
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_voice_config():
    """Test voice configuration loading"""
    try:
        print("Testing voice configuration...")
        
        # Test config loading
        from config.app_config import voice_cfg, voice_model_info
        
        print("✓ Voice configuration loaded successfully")
        print(f"  - Model: {voice_cfg.get('model_name')}")
        print(f"  - Preload: {voice_cfg.get('preload_model')}")
        print(f"  - Batch size: {voice_cfg.get('batch_size')}")
        print(f"  - Workers: {voice_cfg.get('num_workers')}")
        
        # Test model info
        print("\nModel Info:")
        for key, value in voice_model_info.items():
            print(f"  - {key}: {value}")
        
        return True
        
    except Exception as e:
        print(f"❌ Voice configuration test failed: {e}")
        return False

def test_voice_model_preload():
    """Test voice model preloading"""
    try:
        print("\nTesting voice model preloading...")
        
        from config.app_config import voice_model
        
        if voice_model:
            print("✓ Voice model preloaded successfully")
            print(f"  - Model type: {type(voice_model).__name__}")
            
            # Test basic functionality
            current_text = voice_model.get_current_text()
            print(f"  - Current text: '{current_text}'")
            
            return True
        else:
            print("⚠️ Voice model not preloaded (this is OK if preload_model is false)")
            return True
            
    except Exception as e:
        print(f"❌ Voice model preload test failed: {e}")
        return False

def test_voice_api_endpoints():
    """Test voice API endpoints"""
    try:
        print("\nTesting voice API endpoints...")
        
        # Test model info endpoint
        from routers.voice_to_text import get_model_info
        import asyncio
        
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            model_info = loop.run_until_complete(get_model_info())
            print("✓ Model info endpoint works")
            print(f"  - Preloaded: {model_info.get('preloaded')}")
        finally:
            loop.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Voice API test failed: {e}")
        return False

if __name__ == "__main__":
    print("🔊 Voice-to-Text Configuration Test")
    print("=" * 50)
    
    # Test configuration
    config_ok = test_voice_config()
    
    if config_ok:
        # Test model preloading
        preload_ok = test_voice_model_preload()
        
        if preload_ok:
            # Test API endpoints
            api_ok = test_voice_api_endpoints()
            
            if api_ok:
                print("\n✅ All voice configuration tests passed!")
                print("Voice-to-text is properly configured and ready to use.")
            else:
                print("\n❌ API endpoint test failed.")
        else:
            print("\n❌ Model preload test failed.")
    else:
        print("\n❌ Configuration test failed.")
