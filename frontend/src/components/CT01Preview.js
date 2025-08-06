import React, { useState, useEffect, useCallback } from 'react';

function CT01Preview({ formData, cccdData, onConfirm, onChatMessage, handleStepChange, template }) {
  const [docxUrl, setDocxUrl] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const generateFilledDocument = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      console.log('Generating filled HTML document with data:', formData);
      
      // Gọi API để tạo file HTML đã điền sẵn
      const response = await fetch('http://localhost:8000/api/ct01/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          formData,
          cccdData,
          template: {
            code: template?.form_code || 'CT01',
            name: template?.form_title || 'TỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ'
          },
          type: 'html'
        })
      });

      if (!response.ok) {
        throw new Error(`Failed to generate document: ${response.statusText}`);
      }

      // Lấy HTML content đã điền sẵn
      const htmlContent = await response.text();
      
      // Tạo blob URL để hiển thị
      const blob = new Blob([htmlContent], { type: 'text/html' });
      const url = URL.createObjectURL(blob);
      setDocxUrl(url);
      
      console.log('✅ Filled HTML document generated successfully');
      
    } catch (error) {
      console.error('❌ Error generating filled document:', error);
      setError(error.message);
    } finally {
      setLoading(false);
    }
  }, [formData, template, cccdData]);

  useEffect(() => {
    generateFilledDocument();
  }, [generateFilledDocument]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Đang tạo file DOCX với thông tin đã điền...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <div className="mb-4">
          <span className="text-red-500 text-4xl">❌</span>
        </div>
        <h3 className="text-xl font-semibold text-red-600 mb-2">
          Lỗi khi tạo file
        </h3>
        <p className="text-gray-600 mb-4">{error}</p>
        <button
          onClick={generateFilledDocument}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          Thử lại
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6">
        <h3 className="text-2xl font-semibold text-gray-800 mb-2">
          Bước 3: Xem trước biểu mẫu
        </h3>
        <p className="text-gray-600">
          Đây là file CT01.docx đã điền sẵn thông tin của bạn. Kiểm tra lại trước khi nộp.
        </p>
      </div>

      {/* Hiển thị file DOCX đã điền sẵn */}
      <div className="bg-white border-2 border-gray-200 rounded-lg p-4">
        <div className="mb-4 flex justify-between items-center">
          <h4 className="text-lg font-semibold text-gray-800">
            📄 Biểu mẫu CT01 đã điền sẵn thông tin
          </h4>
          <a 
            href={docxUrl} 
            download="CT01-filled.html"
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors text-sm"
          >
            📥 Tải file HTML
          </a>
        </div>

        {/* Embed HTML viewer */}
        <div className="border border-gray-300 rounded-lg overflow-hidden">
          <iframe
            src={docxUrl}
            width="100%"
            height="600px"
            frameBorder="0"
            title="CT01 Filled Document Preview"
            className="w-full"
          />
        </div>

        {/* Thông tin bổ sung */}
        <div className="mt-4 bg-green-50 border border-green-200 rounded-lg p-4">
          <h5 className="font-semibold text-green-800 mb-2">✅ Thông tin đã điền</h5>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <span className="font-medium">Họ tên:</span>
              <span className="ml-2">{formData.ho_ten || 'Chưa điền'}</span>
            </div>
            <div>
              <span className="font-medium">Ngày sinh:</span>
              <span className="ml-2">{formData.ngay_sinh || 'Chưa điền'}</span>
            </div>
            <div>
              <span className="font-medium">Số định danh:</span>
              <span className="ml-2">{formData.so_dinh_danh || 'Chưa điền'}</span>
            </div>
            <div>
              <span className="font-medium">Email:</span>
              <span className="ml-2">{formData.email || 'Chưa điền'}</span>
            </div>
            <div>
              <span className="font-medium">Số điện thoại:</span>
              <span className="ml-2">{formData.dien_thoai || 'Chưa điền'}</span>
            </div>
            <div>
              <span className="font-medium">Chủ hộ:</span>
              <span className="ml-2">{formData.chu_ho || 'Chưa điền'}</span>
            </div>
          </div>
        </div>

        {/* Thông báo */}
        <div className="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start">
            <span className="text-blue-600 mr-2">ℹ️</span>
            <div className="text-sm text-blue-800">
              <p className="font-medium mb-1">Lưu ý:</p>
              <ul className="list-disc list-inside space-y-1">
                <li>File này đã được điền sẵn thông tin từ form</li>
                <li>Bạn có thể tải về để chỉnh sửa thêm nếu cần</li>
                <li>Hoặc tiếp tục để nộp trực tuyến</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-6 flex justify-between">
        <button
          onClick={() => handleStepChange(2)}
          className="px-6 py-3 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors"
        >
          ← Quay lại chỉnh sửa
        </button>
        <button
          onClick={onConfirm}
          className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
        >
          Xác nhận và tiếp tục →
        </button>
      </div>
    </div>
  );
}

export default CT01Preview; 