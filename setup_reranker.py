#!/usr/bin/env python3
"""
Setup script cho BGE Reranker
Cài đặt dependencies và test reranker
"""

import subprocess
import sys

def install_dependencies():
    """Cài đặt dependencies cần thiết cho BGE reranker"""
    print("📦 Installing BGE Reranker dependencies...")
    
    dependencies = [
        "torch",
        "transformers", 
        "sentence-transformers",
        "flagembedding"
    ]
    
    for dep in dependencies:
        try:
            print(f"Installing {dep}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
            print(f"✅ {dep} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {dep}: {e}")
            return False
    
    return True

def test_reranker_import():
    """Test import BGE reranker"""
    print("\n🧪 Testing BGE Reranker import...")
    
    try:
        from services.reranker_service import BGEReranker
        print("✅ BGE Reranker import successful")
        return True
    except ImportError as e:
        print(f"❌ BGE Reranker import failed: {e}")
        return False

def test_reranker_initialization():
    """Test khởi tạo BGE reranker"""
    print("\n🚀 Testing BGE Reranker initialization...")
    
    try:
        from services.reranker_service import BGEReranker
        
        print("Initializing BGE Reranker (this may take a few minutes for first time)...")
        reranker = BGEReranker()
        print("✅ BGE Reranker initialized successfully")
        
        # Test basic functionality
        test_query = "Thủ tục đăng ký thường trú"
        test_docs = [
            {"content": "Đăng ký thường trú cần CMND và sổ hộ khẩu"},
            {"content": "Thủ tục đăng ký thường trú được quy định tại Luật Cư trú"}
        ]
        
        reranked = reranker.rerank(test_query, test_docs, top_k=2)
        print(f"✅ Reranking test successful: {len(reranked)} documents reranked")
        
        return True
        
    except Exception as e:
        print(f"❌ BGE Reranker initialization failed: {e}")
        return False

def check_gpu_availability():
    """Kiểm tra GPU availability"""
    print("\n🖥️ Checking GPU availability...")
    
    try:
        import torch
        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            gpu_name = torch.cuda.get_device_name(0)
            print(f"✅ GPU available: {gpu_name} (Count: {gpu_count})")
            return True
        else:
            print("⚠️ GPU not available, will use CPU (slower but functional)")
            return False
    except Exception as e:
        print(f"❌ GPU check failed: {e}")
        return False

def main():
    """Main setup function"""
    print("🎯 BGE Reranker Setup")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        sys.exit(1)
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Dependency installation failed")
        sys.exit(1)
    
    # Check GPU
    check_gpu_availability()
    
    # Test import
    if not test_reranker_import():
        print("❌ Import test failed")
        sys.exit(1)
    
    # Test initialization
    if not test_reranker_initialization():
        print("❌ Initialization test failed")
        sys.exit(1)
    
    print("\n🎉 BGE Reranker setup completed successfully!")
    print("\n📝 Next steps:")
    print("1. Run the main application: python main.py")
    print("2. Test reranking: python test_reranker.py")
    print("3. Check logs for reranking performance")

if __name__ == "__main__":
    main() 