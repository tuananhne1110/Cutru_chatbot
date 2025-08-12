import React, { useState } from 'react';
import CT01Modal from './CT01Modal';

function CT01TestPage() {
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleChatMessage = (message) => {
    // Handle chat message if needed
  };

  const openModal = () => {
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
  };

  return (
    <div className="min-h-screen relative">
      {/* Portal Background - y hệt như UI.html */}
      <div className="fixed inset-0 bg-gradient-to-br from-blue-500 to-purple-600 flex flex-col items-center justify-center text-white text-center z-10">
        <div className="portal-header">
          <h1 className="text-5xl font-semibold mb-3">Chính phủ Điện tử Việt Nam</h1>
          <p className="text-xl opacity-90 mb-10">Cổng thông tin và dịch vụ công trực tuyến</p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 max-w-6xl w-full px-5">
          <div 
            onClick={openModal}
            className="bg-white bg-opacity-10 backdrop-blur-md border border-white border-opacity-20 rounded-2xl p-8 text-center cursor-pointer transition-all duration-300 hover:bg-white hover:bg-opacity-20 hover:-translate-y-1"
          >
            <div className="text-4xl mb-4">📝</div>
            <div className="text-xl font-semibold mb-2">Điền biểu mẫu CT01</div>
            <div className="text-sm opacity-80">Tờ khai thuế thu nhập cá nhân</div>
          </div>
          
          <div className="bg-white bg-opacity-10 backdrop-blur-md border border-white border-opacity-20 rounded-2xl p-8 text-center cursor-pointer transition-all duration-300 hover:bg-white hover:bg-opacity-20 hover:-translate-y-1">
            <div className="text-4xl mb-4">📄</div>
            <div className="text-xl font-semibold mb-2">Thủ tục hành chính</div>
            <div className="text-sm opacity-80">Hướng dẫn các thủ tục hành chính phổ biến</div>
          </div>
          
          <div className="bg-white bg-opacity-10 backdrop-blur-md border border-white border-opacity-20 rounded-2xl p-8 text-center cursor-pointer transition-all duration-300 hover:bg-white hover:bg-opacity-20 hover:-translate-y-1">
            <div className="text-4xl mb-4">🏢</div>
            <div className="text-xl font-semibold mb-2">Đăng ký kinh doanh</div>
            <div className="text-sm opacity-80">Thủ tục đăng ký doanh nghiệp và hộ kinh doanh</div>
          </div>
          
          <div className="bg-white bg-opacity-10 backdrop-blur-md border border-white border-opacity-20 rounded-2xl p-8 text-center cursor-pointer transition-all duration-300 hover:bg-white hover:bg-opacity-20 hover:-translate-y-1">
            <div className="text-4xl mb-4">🎓</div>
            <div className="text-xl font-semibold mb-2">Giáo dục</div>
            <div className="text-sm opacity-80">Thông tin tuyển sinh và dịch vụ giáo dục</div>
          </div>
          
          <div className="bg-white bg-opacity-10 backdrop-blur-md border border-white border-opacity-20 rounded-2xl p-8 text-center cursor-pointer transition-all duration-300 hover:bg-white hover:bg-opacity-20 hover:-translate-y-1">
            <div className="text-4xl mb-4">⚖️</div>
            <div className="text-xl font-semibold mb-2">Pháp luật</div>
            <div className="text-sm opacity-80">Tra cứu văn bản pháp luật và quy định</div>
          </div>
          
          <div className="bg-white bg-opacity-10 backdrop-blur-md border border-white border-opacity-20 rounded-2xl p-8 text-center cursor-pointer transition-all duration-300 hover:bg-white hover:bg-opacity-20 hover:-translate-y-1">
            <div className="text-4xl mb-4">💰</div>
            <div className="text-xl font-semibold mb-2">Dịch vụ thuế</div>
            <div className="text-sm opacity-80">Tra cứu và nộp thuế trực tuyến</div>
          </div>
          
          <div className="bg-white bg-opacity-10 backdrop-blur-md border border-white border-opacity-20 rounded-2xl p-8 text-center cursor-pointer transition-all duration-300 hover:bg-white hover:bg-opacity-20 hover:-translate-y-1">
            <div className="text-4xl mb-4">🏥</div>
            <div className="text-xl font-semibold mb-2">Dịch vụ y tế</div>
            <div className="text-sm opacity-80">Đặt lịch khám và tra cứu thông tin y tế</div>
          </div>
        </div>
      </div>

      {/* CT01 Modal */}
      <CT01Modal
        isOpen={isModalOpen}
        onClose={closeModal}
        onChatMessage={handleChatMessage}
      />
    </div>
  );
}

export default CT01TestPage; 