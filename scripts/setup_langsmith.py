#!/usr/bin/env python3
"""
Setup script cho LangSmith integration.
Chạy script này để setup LangSmith một cách tự động.
"""

import os
import sys
import shutil
from pathlib import Path

def print_header():
    """In header đẹp"""
    print("🎯 LangSmith Setup Script")
    print("=" * 50)
    print("This script will help you set up LangSmith integration for your Cutru Chatbot.")
    print()

def check_dependencies():
    """Kiểm tra dependencies"""
    print("📋 Checking dependencies...")
    
    try:
        import langsmith
        print("✅ langsmith package is installed")
        return True
    except ImportError:
        print("❌ langsmith package not found")
        print("Please install it with: pip install langsmith==0.2.14")
        return False

def setup_env_file():
    """Setup .env file"""
    print("\n🔧 Setting up environment file...")
    
    env_example_path = Path(".env.example")
    env_path = Path(".env")
    
    if not env_example_path.exists():
        print("❌ .env.example file not found!")
        return False
    
    if env_path.exists():
        print("⚠️  .env file already exists")
        response = input("Do you want to backup and recreate it? (y/N): ").strip().lower()
        if response == 'y':
            # Backup existing .env
            backup_path = f".env.backup.{int(__import__('time').time())}"
            shutil.copy(env_path, backup_path)
            print(f"📁 Backed up existing .env to {backup_path}")
        else:
            print("ℹ️  Keeping existing .env file")
            return True
    
    # Copy .env.example to .env
    shutil.copy(env_example_path, env_path)
    print("✅ Created .env file from .env.example")
    return True

def get_langsmith_api_key():
    """Get LangSmith API key from user"""
    print("\n🔑 LangSmith API Key Setup")
    print("To get your API key:")
    print("1. Visit https://smith.langchain.com/")
    print("2. Sign up or log in")
    print("3. Go to Settings > API Keys")
    print("4. Create a new API key")
    print()
    
    api_key = input("Enter your LangSmith API key (or press Enter to skip): ").strip()
    
    if not api_key:
        print("⏭️  Skipping API key setup")
        print("   You can add it later to your .env file")
        return None
    
    return api_key

def update_env_file(api_key, project_name):
    """Update .env file with user inputs"""
    print("\n📝 Updating .env file...")
    
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ .env file not found!")
        return False
    
    # Read current content
    with open(env_path, 'r') as f:
        content = f.read()
    
    # Update API key if provided
    if api_key:
        content = content.replace(
            "LANGCHAIN_API_KEY=your_langsmith_api_key_here",
            f"LANGCHAIN_API_KEY={api_key}"
        )
        print("✅ Updated LANGCHAIN_API_KEY")
    
    # Update project name if provided
    if project_name:
        content = content.replace(
            "LANGCHAIN_PROJECT=cutru-chatbot",
            f"LANGCHAIN_PROJECT={project_name}"
        )
        print(f"✅ Updated LANGCHAIN_PROJECT to {project_name}")
    
    # Ensure tracing is enabled
    if "LANGCHAIN_TRACING_V2=false" in content:
        content = content.replace(
            "LANGCHAIN_TRACING_V2=false",
            "LANGCHAIN_TRACING_V2=true"
        )
    elif "LANGCHAIN_TRACING_V2=your_langsmith_api_key_here" in content:
        content = content.replace(
            "LANGCHAIN_TRACING_V2=your_langsmith_api_key_here",
            "LANGCHAIN_TRACING_V2=true"
        )
    
    # Write updated content
    with open(env_path, 'w') as f:
        f.write(content)
    
    return True

def setup_project_config():
    """Setup project configuration"""
    print("\n⚙️  Project Configuration")
    
    project_name = input("Enter your LangSmith project name (default: cutru-chatbot): ").strip()
    if not project_name:
        project_name = "cutru-chatbot"
    
    environment = input("Enter environment (development/staging/production, default: development): ").strip()
    if not environment:
        environment = "development"
    
    return project_name, environment

def update_config_yaml(environment):
    """Update config.yaml with environment"""
    print("\n📄 Updating config.yaml...")
    
    config_path = Path("config/config.yaml")
    if not config_path.exists():
        print("⚠️  config/config.yaml not found, skipping update")
        return
    
    with open(config_path, 'r') as f:
        content = f.read()
    
    # Update environment in metadata
    if 'environment: "production"' in content:
        content = content.replace(
            'environment: "production"',
            f'environment: "{environment}"'
        )
        print(f"✅ Updated environment to {environment}")
    
    # Update tags with environment
    if environment != "production":
        content = content.replace(
            '- "production"',
            f'- "{environment}"'
        )
        print(f"✅ Updated tags with {environment}")
    
    with open(config_path, 'w') as f:
        f.write(content)

def print_next_steps(project_name):
    """Print next steps"""
    print(f"\n🎉 Setup Complete!")
    print("=" * 50)
    print("Next steps:")
    print()
    print("1. 🚀 Start your application:")
    print("   python main.py")
    print()
    print("2. 🧪 Test LangSmith integration:")
    print("   python scripts/test_langsmith.py")
    print()
    print("3. 📊 View your dashboard:")
    print("   https://smith.langchain.com/")
    print(f"   Project: {project_name}")
    print()
    print("4. 💬 Send some test messages to create traces")
    print()
    print("📚 For more information, read:")
    print("   docs/langsmith-integration.md")
    print()
    print("🎊 Happy monitoring with LangSmith!")

def main():
    """Main setup function"""
    print_header()
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Setup .env file
    if not setup_env_file():
        sys.exit(1)
    
    # Get project configuration
    project_name, environment = setup_project_config()
    
    # Get API key
    api_key = get_langsmith_api_key()
    
    # Update .env file
    if not update_env_file(api_key, project_name):
        sys.exit(1)
    
    # Update config.yaml
    update_config_yaml(environment)
    
    # Print next steps
    print_next_steps(project_name)

if __name__ == "__main__":
    main()