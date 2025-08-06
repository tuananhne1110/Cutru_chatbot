// Test script để kiểm tra template từ Supabase
const testTemplate = async () => {
  try {
    // Mock environment variables
    process.env.REACT_APP_SUPABASE_URL = 'https://rjrqtogyzmgyqvryxfyk.supabase.co';
    process.env.REACT_APP_SUPABASE_ANON_KEY = 'your_supabase_anon_key_here';

    // Import service
    const { ct01Service } = require('./src/services/ct01Service');
    
    console.log('🔄 Đang test template từ Supabase...');
    
    // Test getCT01Template
    const template = await ct01Service.getCT01Template();
    
    console.log('✅ Template loaded successfully:');
    console.log('Code:', template.code);
    console.log('Name:', template.name);
    console.log('Description:', template.description);
    console.log('File URL:', template.file_url);
    console.log('Fields count:', template.fields?.length || 0);
    
    if (template.fields) {
      console.log('\n📋 Fields:');
      template.fields.forEach((field, index) => {
        console.log(`${index + 1}. ${field.label} (${field.name}) - ${field.type}${field.required ? ' *' : ''}`);
      });
    }
    
    console.log('\n🎉 Test completed successfully!');
    
  } catch (error) {
    console.error('❌ Test failed:', error.message);
    console.log('\n💡 Hints:');
    console.log('1. Kiểm tra REACT_APP_SUPABASE_ANON_KEY');
    console.log('2. Kiểm tra database có bảng forms không');
    console.log('3. Kiểm tra có record CT01 không');
  }
};

// Run test
testTemplate(); 