import React from 'react';

function DemoPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-800 mb-4">
            Chính phủ Điện tử Việt Nam
          </h1>
          <p className="text-xl text-gray-600">
            Cổng thông tin và dịch vụ công trực tuyến
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
          <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
            <div className="text-3xl mb-4">📋</div>
            <h3 className="text-lg font-semibold mb-2">Thủ tục hành chính</h3>
            <p className="text-gray-600 text-sm">
              Hướng dẫn các thủ tục hành chính phổ biến
            </p>
          </div>

          <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
            <div className="text-3xl mb-4">🏢</div>
            <h3 className="text-lg font-semibold mb-2">Đăng ký kinh doanh</h3>
            <p className="text-gray-600 text-sm">
              Thủ tục đăng ký doanh nghiệp và hộ kinh doanh
            </p>
          </div>

          <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
            <div className="text-3xl mb-4">💰</div>
            <h3 className="text-lg font-semibold mb-2">Dịch vụ thuế</h3>
            <p className="text-gray-600 text-sm">
              Tra cứu và nộp thuế trực tuyến
            </p>
          </div>

          <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
            <div className="text-3xl mb-4">🏥</div>
            <h3 className="text-lg font-semibold mb-2">Dịch vụ y tế</h3>
            <p className="text-gray-600 text-sm">
              Đặt lịch khám và tra cứu thông tin y tế
            </p>
          </div>

          <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
            <div className="text-3xl mb-4">🎓</div>
            <h3 className="text-lg font-semibold mb-2">Giáo dục</h3>
            <p className="text-gray-600 text-sm">
              Thông tin tuyển sinh và dịch vụ giáo dục
            </p>
          </div>

          <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
            <div className="text-3xl mb-4">⚖️</div>
            <h3 className="text-lg font-semibold mb-2">Pháp luật</h3>
            <p className="text-gray-600 text-sm">
              Tra cứu văn bản pháp luật và quy định
            </p>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-md p-8 text-center">
          <h2 className="text-2xl font-bold text-gray-800 mb-4">
            Cần hỗ trợ?
          </h2>
          <p className="text-gray-600 mb-6">
            Trợ lý ảo của chúng tôi luôn sẵn sàng hỗ trợ bạn 24/7. 
            Hãy click vào nút chat ở góc phải dưới màn hình để được tư vấn.
          </p>
          <div className="flex justify-center space-x-4">
            <div className="text-center">
              <div className="text-2xl mb-2">🤖</div>
              <p className="text-sm text-gray-600">Trợ lý Ảo</p>
            </div>
            <div className="text-center">
              <div className="text-2xl mb-2">📞</div>
              <p className="text-sm text-gray-600">Hotline</p>
            </div>
            <div className="text-center">
              <div className="text-2xl mb-2">📧</div>
              <p className="text-sm text-gray-600">Email</p>
            </div>
          </div>
        </div>

        <div className="mt-8 text-center text-gray-500 text-sm">
          <p>© 2024 Chính phủ điện tử Việt Nam. Được phát triển để phục vụ nhân dân.</p>
        </div>
      </div>
    </div>
  );
}

export default DemoPage; 