import React, { useState, useEffect, useRef } from 'react';
import CCCDScanner from './CCCDScanner';
import CT01Form from './CT01Form';
import CT01Preview from './CT01Preview';
import CT01Complete from './CT01Complete';
import { ct01Service } from '../services/ct01Service';

function CT01Modal({ isOpen, onClose, onChatMessage }) {
  const [currentStep, setCurrentStep] = useState(1);
  const [cccdData, setCccdData] = useState(null);
  const [formData, setFormData] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [template, setTemplate] = useState(null);
  const [templateLoading, setTemplateLoading] = useState(false);
  const formRef = useRef(null);

  const steps = [
    { id: 1, title: 'Quét CCCD', description: 'Quét thẻ căn cước công dân' },
    { id: 2, title: 'Điền thông tin', description: 'Điền thông tin biểu mẫu CT01' },
    { id: 3, title: 'Xem trước', description: 'Kiểm tra thông tin trước khi nộp' },
    { id: 4, title: 'Hoàn tất', description: 'Tải về và nộp hồ sơ' }
  ];

  // Load template khi modal mở
  useEffect(() => {
    if (isOpen && !template) {
      loadTemplate();
    }
  }, [isOpen, template]);

  const loadTemplate = async () => {
    setTemplateLoading(true);
    try {
      console.log('Loading CT01 template from Supabase...');
      const templateData = await ct01Service.getCT01Template();
      console.log('Template loaded:', templateData);
      setTemplate(templateData);
    } catch (error) {
      console.error('Error loading template:', error);
    } finally {
      setTemplateLoading(false);
    }
  };

  const handleStepChange = (step) => {
    if (step >= 1 && step <= 4) {
      setCurrentStep(step);
      updateProgress(step);
    }
  };

  const updateProgress = (step) => {
    const progressText = document.getElementById('progressText');
    if (progressText) {
      const stepNames = ['Quét CCCD', 'Điền thông tin', 'Xem trước', 'Hoàn tất'];
      progressText.textContent = `Bước ${step}/4: ${stepNames[step - 1]}`;
    }
  };

  const handleCCCDScanned = (data) => {
    setCccdData(data);
    // Convert DD/MM/YYYY to YYYY-MM-DD for form input
    const convertDate = (dateStr) => {
      if (!dateStr) return '';
      const parts = dateStr.split('/');
      if (parts.length === 3) {
        return `${parts[2]}-${parts[1].padStart(2, '0')}-${parts[0].padStart(2, '0')}`;
      }
      return dateStr;
    };
    
    setFormData({
      ho_ten: data.personName || '',
      so_dinh_danh: data.idCode || '',
      ngay_sinh: convertDate(data.dateOfBirth) || '',
      gioi_tinh: data.gender || '',
      dia_chi: data.residencePlace || '',
      // Chỉ giữ các trường thực sự có trong form CT01
      dien_thoai: '',
      email: '',
      chu_ho: '',
      quan_he_chu_ho: '',
      dinh_danh_chu_ho: '',
      noi_dung_de_nghi: ''
    });
    handleStepChange(2);
  };

  const handleFormSubmit = (data) => {
    console.log('🔍 Saving form data from step 2:', data);
    setFormData(data);
    handleStepChange(3);
  };

  const handlePreviewConfirm = () => {
    handleStepChange(4);
  };

  const handleDownload = async (type) => {
    setIsLoading(true);
    try {
      // Sử dụng ct01Service để tạo file với template
      const blob = await ct01Service.generateCT01File(formData, cccdData, template, type);
      
      // Download file
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${template?.code || 'CT01'}-${Date.now()}.${type}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      console.log(`File ${type} đã được tải xuống từ template: ${template?.template_url || template?.file_url}`);
    } catch (error) {
      console.error('Error downloading file:', error);
      alert('Có lỗi xảy ra khi tải file. Vui lòng thử lại.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmitOnline = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/ct01/submit', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          formData,
          cccdData
        })
      });
      
      if (response.ok) {
        // Success handled silently
      }
    } catch (error) {
      console.error('Error submitting form:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    setCurrentStep(1);
    setCccdData(null);
    setFormData({});
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[2000] backdrop-blur-sm">
      <div className="bg-white w-[90%] max-w-[1000px] h-[90%] rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-[modalSlideIn_0.3s_ease]">
        {/* Header - y hệt như UI.html */}
        <div className="bg-gradient-to-r from-green-500 to-teal-500 text-white p-6 rounded-t-2xl flex justify-between items-center">
          <div className="flex items-center space-x-3">
            <span className="text-2xl">📝</span>
            <div>
              <h2 className="text-xl font-semibold">
                {templateLoading ? 'Đang tải template...' : 
                 template ? `Biểu mẫu ${template.code} - ${template.name}` : 
                 'Biểu mẫu CT01 - Tờ khai thuế thu nhập cá nhân'}
              </h2>
              <p className="text-sm opacity-90">
                {template ? template.description : 'Hệ thống tự động điền từ CCCD'}
              </p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="bg-white bg-opacity-20 hover:bg-opacity-30 rounded-full p-2 transition-all"
          >
            <span className="text-xl">×</span>
          </button>
        </div>

        {/* Content */}
        <div className="flex flex-1 overflow-hidden">
          {/* Sidebar - y hệt như UI.html */}
          <div className="w-64 bg-gray-50 border-r border-gray-200 p-6">
            <ul className="space-y-4">
              {steps.map((step) => (
                <li
                  key={step.id}
                  onClick={() => handleStepChange(step.id)}
                  className={`flex items-center space-x-3 p-3 rounded-lg cursor-pointer transition-all ${
                    currentStep === step.id
                      ? 'bg-green-500 text-white'
                      : 'hover:bg-gray-100'
                  }`}
                >
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold ${
                    currentStep === step.id
                      ? 'bg-white text-green-500'
                      : 'bg-gray-200 text-gray-600'
                  }`}>
                    {step.id}
                  </div>
                  <div>
                    <div className="font-medium">{step.title}</div>
                    <div className={`text-xs ${
                      currentStep === step.id ? 'text-white opacity-90' : 'text-gray-500'
                    }`}>
                      {step.description}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          {/* Main Content */}
          <div className="flex-1 p-6 overflow-y-auto">
            {currentStep === 1 && (
              <CCCDScanner
                onScanned={handleCCCDScanned}
                onChatMessage={onChatMessage}
              />
            )}
            {currentStep === 2 && (
              <CT01Form
                ref={formRef}
                cccdData={cccdData}
                formData={formData}
                onSubmit={handleFormSubmit}
                onChatMessage={onChatMessage}
                template={template}
              />
            )}
            {currentStep === 3 && (
              <CT01Preview
                formData={formData}
                cccdData={cccdData}
                onConfirm={handlePreviewConfirm}
                onChatMessage={onChatMessage}
                handleStepChange={handleStepChange}
                template={template}
              />
            )}
            {currentStep === 4 && (
              <CT01Complete
                formData={formData}
                cccdData={cccdData}
                onDownload={handleDownload}
                onSubmitOnline={handleSubmitOnline}
                isLoading={isLoading}
                onChatMessage={onChatMessage}
                onClose={handleClose}
                setCurrentStep={setCurrentStep}
                setCccdData={setCccdData}
                setFormData={setFormData}
                template={template}
              />
            )}
          </div>
        </div>

        {/* Action Bar - y hệt như UI.html */}
        <div className="border-t border-gray-200 p-6 bg-gray-50 flex justify-between items-center">
          <div className="text-sm text-gray-600" id="progressText">
            Bước {currentStep}/4: {steps[currentStep - 1]?.title}
          </div>
          <div className="flex space-x-3">
            {currentStep > 1 && (
              <button
                onClick={() => handleStepChange(currentStep - 1)}
                className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors"
              >
                ← Quay lại
              </button>
            )}
            {currentStep < 4 && (
              <button
                onClick={() => {
                  if (currentStep === 2) {
                    // Gọi handleSubmit của form trước khi chuyển bước
                    if (formRef.current) {
                      formRef.current.handleSubmit();
                    }
                  } else {
                    handleStepChange(currentStep + 1);
                  }
                }}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Tiếp theo →
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default CT01Modal; 