import React from 'react';

function CT01Complete({ formData, cccdData, onDownload, onSubmitOnline, isLoading, onChatMessage, onClose, setCurrentStep, setCccdData, setFormData, template }) {
  const referenceId = `CT01-${new Date().getFullYear()}-${Math.random().toString(36).substr(2, 6).toUpperCase()}`;

  const handleDownload = (type) => {
    console.log('Downloading file with type:', type);
    console.log('Form data:', formData);
    console.log('Template:', template);
    onDownload(type, template);
  };

  const handleSubmitOnline = () => {
    onSubmitOnline();
  };

  return (
    <div className="text-center py-8">
      <div className="mb-8">
        <h3 className="text-2xl font-semibold text-gray-800 mb-2">
          Bước 4: Hoàn tất và tải về
        </h3>
        <p className="text-gray-600">
          Biểu mẫu {template?.code || 'CT01'} đã được tạo thành công từ file DOCX gốc. Bạn có thể tải về hoặc nộp trực tuyến.
        </p>
      </div>

      <div className="mb-8">
        <div className="w-24 h-24 bg-green-500 rounded-full flex items-center justify-center mx-auto mb-4">
          <span className="text-4xl">✅</span>
        </div>
        <h4 className="text-xl font-semibold text-green-600 mb-2">
          Biểu mẫu {template?.code || 'CT01'} đã sẵn sàng!
        </h4>
        <p className="text-gray-600">
          Vui lòng chọn hành động tiếp theo:
        </p>
      </div>

      <div className="flex justify-center space-x-4 mb-8 flex-wrap">
        <button
          onClick={() => handleDownload('docx')}
          disabled={isLoading}
          className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-2"
        >
          <span>📝</span>
          <span>Tải xuống DOCX</span>
        </button>
        <button
          onClick={() => handleDownload('pdf')}
          disabled={isLoading}
          className="px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-2"
        >
          <span>📄</span>
          <span>Tải xuống PDF</span>
        </button>
        <button
          onClick={handleSubmitOnline}
          disabled={isLoading}
          className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-2"
        >
          <span>🌐</span>
          <span>Nộp trực tuyến</span>
        </button>
      </div>

      {isLoading && (
        <div className="text-center py-4">
          <div className="inline-flex items-center space-x-2 text-blue-600">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
            <span>Đang xử lý...</span>
          </div>
        </div>
      )}

      <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 max-w-md mx-auto">
        <h5 className="font-semibold text-gray-800 mb-4">📋 Thông tin hồ sơ</h5>
        <div className="space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-600">Mã tham chiếu:</span>
            <span className="font-mono text-gray-800">{referenceId}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Thời gian tạo:</span>
            <span className="text-gray-800">{new Date().toLocaleString('vi-VN')}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Trạng thái:</span>
            <span className="text-green-600 font-semibold">Hoàn tất</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Người nộp:</span>
            <span className="text-gray-800">{formData.ho_ten || 'N/A'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Số CCCD:</span>
            <span className="text-gray-800">{formData.so_dinh_danh || formData.so_cccd || 'N/A'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Template:</span>
            <span className="text-gray-800">DOCX từ Supabase</span>
          </div>
        </div>
      </div>

      <div className="mt-8 text-center">
        <p className="text-sm text-gray-500 mb-4">
          💡 Mẹo: Lưu mã tham chiếu để tra cứu kết quả sau này
        </p>
        <div className="flex justify-center space-x-4">
          <button
            onClick={() => onClose()}
            className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors"
          >
            Về trang chủ
          </button>
          <button
            onClick={() => {
              onClose();
              // Reset form and start over
              setCurrentStep(1);
              setCccdData(null);
              setFormData({});
            }}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
          >
            Tạo mới
          </button>
        </div>
      </div>
    </div>
  );
}

export default CT01Complete; 