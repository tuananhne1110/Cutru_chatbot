import React, { useState, useEffect, useCallback, useRef } from 'react';
import { renderAsync } from 'docx-preview';

function CT01Preview({ formData, cccdData, onConfirm, onChatMessage, handleStepChange, template }) {
  const [docxUrl, setDocxUrl] = useState(null);
  const [docxContent, setDocxContent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const previewRef = useRef(null);

  const generateFilledDocument = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      console.log('Generating filled DOCX document for preview with data:', formData);
      
      // Tạo file DOCX cho preview
      const previewResponse = await fetch('http://localhost:8000/api/ct01/preview', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          formData,
          cccdData
        })
      });

      if (!previewResponse.ok) {
        throw new Error(`Failed to generate preview: ${previewResponse.statusText}`);
      }

      const previewData = await previewResponse.json();
      const previewUrl = `http://localhost:8000/api/ct01/preview/${previewData.file_path.split('/').pop()}`;
      
      setDocxUrl(previewUrl);
      
      // Tải nội dung DOCX để render
      const docxResponse = await fetch(previewUrl);
      const docxBlob = await docxResponse.blob();
      setDocxContent(docxBlob);
      
      console.log('✅ Preview URL generated successfully:', previewUrl);
      
    } catch (error) {
      console.error('❌ Error generating preview:', error);
      setError(error.message);
    } finally {
      setLoading(false);
    }
  }, [formData, template, cccdData]);

  // Function để tải xuống DOCX đã có
  const downloadDocx = () => {
    if (docxUrl) {
      const link = document.createElement('a');
      link.href = docxUrl;
      link.download = 'CT01-filled.docx';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      console.log('✅ DOCX downloaded successfully');
    } else {
      alert('Chưa có file DOCX để tải xuống. Vui lòng thử lại.');
    }
  };

  useEffect(() => {
    generateFilledDocument();
  }, [generateFilledDocument]);

  // Render DOCX khi có content
  useEffect(() => {
    if (docxContent && previewRef.current) {
      renderAsync(docxContent, previewRef.current, previewRef.current, {
        className: 'docx-preview',
        inWrapper: true,
        ignoreWidth: false,
        ignoreHeight: false,
        ignoreFonts: false,
        breakPages: true,
        ignoreLastRenderedPageBreak: true,
        experimental: true,
        trimXmlDeclaration: true,
        useBase64URL: true,
        useMathMLPolyfill: true,
        renderEndnotes: true,
        renderFooters: true,
        renderFootnotes: true,
        renderHeaders: true,
        ignoreMarginTop: false,
        ignoreMarginBottom: false,
        ignoreMarginLeft: false,
        ignoreMarginRight: false,
        ignorePaddingTop: false,
        ignorePaddingBottom: false,
        ignorePaddingLeft: false,
        ignorePaddingRight: false,
        ignoreBorderTop: false,
        ignoreBorderBottom: false,
        ignoreBorderLeft: false,
        ignoreBorderRight: false,
        renderComments: false,
        renderChanges: false,
        renderNumbering: true,
        renderFootnotes: true,
        renderEndnotes: true,
        renderHeaders: true,
        renderFooters: true,
              }).catch(error => {
        console.error('❌ Error rendering DOCX:', error);
        setError('Không thể hiển thị preview của file DOCX');
      });
    }
  }, [docxContent]);

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
        <div className="mb-4">
          <h4 className="text-lg font-semibold text-gray-800">
            Biểu mẫu CT01 đã điền sẵn thông tin
          </h4>
        </div>

        {/* Embed DOCX viewer hoặc hiển thị thông tin */}
        <div className="border border-gray-300 rounded-lg overflow-hidden">
          {docxUrl ? (
            <div className="bg-white">
              {/* DOCX Preview */}
              <div className="p-4 border-b bg-gray-50">
                <h5 className="text-lg font-semibold text-gray-800 mb-2">
                  Xem trước file DOCX
                </h5>
                <p className="text-sm text-gray-600">
                  File CT01.docx đã được điền đầy đủ thông tin từ form của bạn.
                </p>
              </div>
              
              {/* DOCX Preview - Sử dụng docx-preview */}
              <div className="bg-gray-100 p-6" style={{ minHeight: '600px', maxHeight: '800px', overflow: 'auto', paddingLeft: '5px', paddingRight: '5px' }}>
                {docxContent ? (
                  <div className="bg-white rounded-lg shadow-sm p-4 w-full">
                    <div className="text-center mb-4">
                      <h3 className="text-lg font-bold text-gray-800 mb-2">Xem trước biểu mẫu CT01</h3>
                      <p className="text-sm text-gray-600">Kiểm tra lại thông tin trước khi tiếp tục</p>
                    </div>
                    
                    {/* Hiển thị file DOCX thực tế - sử dụng docx-preview */}
                    <div 
                      ref={previewRef}
                      className="border border-gray-300 bg-white"
                      style={{ 
                        minHeight: '600px',
                        maxHeight: '700px',
                        overflow: 'auto',
                        paddingLeft: '40px',
                        paddingRight: '40px',
                        marginLeft: '-20px',
                        marginRight: '-20px'
                      }}
                    />
                    
                    <div className="mt-4 text-center text-xs text-gray-500">
                      <p>Đây là preview của biểu mẫu CT01 đã được điền thông tin</p>
                      <p>Kiểm tra lại tất cả thông tin trước khi tiếp tục</p>
                    </div>
                  </div>
                ) : (
                  <div className="bg-white rounded-lg shadow-sm p-6 max-w-4xl mx-auto">
                    <div className="text-center">
                      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
                      <p className="text-gray-600">Đang tạo file DOCX...</p>
                    </div>
                  </div>
                )}
              </div>
              

            </div>
          ) : (
            <div className="p-8 text-center bg-gray-50">
              <div className="text-6xl mb-4">📄</div>
              <h5 className="text-lg font-semibold text-gray-800 mb-2">
                File DOCX đã được tạo thành công!
              </h5>
              <p className="text-gray-600 mb-4">
                File CT01.docx đã được điền đầy đủ thông tin từ form của bạn.
              </p>
              <div className="flex justify-center space-x-4">
                <a 
                  href={docxUrl} 
                  download="CT01-filled.docx"
                  className="bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700 transition-colors"
                >
                  Tải xuống DOCX
                </a>
                <button
                  onClick={() => window.open(docxUrl, '_blank')}
                  className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Xem file
                </button>
              </div>
            </div>
          )}
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
                <li>File được tạo từ template DOCX gốc từ Supabase</li>
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