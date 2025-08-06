import React, { useState, useEffect } from 'react';

const CT01Form = React.forwardRef(({ cccdData, formData, onSubmit, onChatMessage, template }, ref) => {
  const [localFormData, setLocalFormData] = useState(formData);
  const [autoFilledFields, setAutoFilledFields] = useState(new Set());

  useEffect(() => {
    // Debug: log template và form data
    console.log('🔍 Template fields:', template?.fields?.map(f => f.id));
    console.log('🔍 CCCD data:', cccdData);
    console.log('🔍 Initial formData:', formData);
    
    // Khởi tạo form data từ props hoặc CCCD data
    const initialData = { ...formData };
    const autoFilled = new Set();
    
    if (cccdData && Object.keys(cccdData).length > 0) {
      // Map CCCD data to template fields
      if (cccdData.personName) {
        initialData.ho_ten = cccdData.personName;
        autoFilled.add('ho_ten');
      }
      if (cccdData.idCode) {
        initialData.so_dinh_danh = cccdData.idCode;
        autoFilled.add('so_dinh_danh');
      }
      if (cccdData.dateOfBirth) {
        // Convert DD/MM/YYYY to YYYY-MM-DD for form input
        const parts = cccdData.dateOfBirth.split('/');
        if (parts.length === 3) {
          initialData.ngay_sinh = `${parts[2]}-${parts[1].padStart(2, '0')}-${parts[0].padStart(2, '0')}`;
          autoFilled.add('ngay_sinh');
        }
      }
      if (cccdData.gender) {
        initialData.gioi_tinh = cccdData.gender;
        autoFilled.add('gioi_tinh');
      }
      if (cccdData.residencePlace) {
        initialData.dia_chi = cccdData.residencePlace;
        autoFilled.add('dia_chi');
      }
      // Không auto-fill số điện thoại và email - để user tự điền
      // Những trường này không có trong CCCD thật
    }
    
    console.log('🔍 Final initialData:', initialData);
    console.log('🔍 Auto-filled fields:', Array.from(autoFilled));
    
    setLocalFormData(initialData);
    setAutoFilledFields(autoFilled);
  }, [cccdData, formData, template]);

  // Sync localFormData với formData từ parent khi formData thay đổi
  useEffect(() => {
    if (formData && Object.keys(formData).length > 0) {
      console.log('🔍 Syncing localFormData with parent formData:', formData);
      setLocalFormData(prev => ({ ...prev, ...formData }));
    }
  }, [formData]);

  // Debug: log localFormData khi nó thay đổi
  useEffect(() => {
    console.log('🔍 localFormData changed:', localFormData);
  }, [localFormData]);

  const handleInputChange = (field, value) => {
    console.log(`🔍 Input changed: ${field} = "${value}"`);
    setLocalFormData(prev => {
      const newData = {
        ...prev,
        [field]: value
      };
      console.log(`🔍 Updated localFormData:`, newData);
      return newData;
    });
  };

  const handleSubmit = () => {
    console.log('🔍 handleSubmit called!');
    
    // Debug: log dữ liệu trước khi submit
    console.log('🔍 Form data before submit:', localFormData);
    console.log('🔍 dien_thoai:', localFormData.dien_thoai);
    console.log('🔍 email:', localFormData.email);
    
    // Debug: check if any fields are required
    console.log('🔍 Template fields:', template?.fields);
    console.log('🔍 Required fields:', template?.fields?.filter(field => field.required)?.map(field => field.id));
    
    // Validate required fields based on template
    const requiredFields = template?.fields?.filter(field => field.required)?.map(field => field.id) || [];
    const missingFields = requiredFields.filter(field => !localFormData[field]);
    
    console.log('🔍 Missing fields:', missingFields);
    console.log('🔍 Validation passed, proceeding with submit...');
    
    if (missingFields.length > 0) {
      const fieldNames = template?.fields?.reduce((acc, field) => {
        acc[field.id] = field.label;
        return acc;
      }, {}) || {};
      const missingFieldNames = missingFields.map(field => fieldNames[field]).join(', ');
      alert(`⚠️ Vui lòng điền đầy đủ các trường bắt buộc: ${missingFieldNames}`);
      return;
    }
    
    console.log('🔍 Calling onSubmit with data:', localFormData);
    onSubmit(localFormData);
  };

  const isAutoFilled = (field) => autoFilledFields.has(field);

  // Expose handleSubmit through ref
  React.useImperativeHandle(ref, () => ({
    handleSubmit
  }));

  return (
    <div>
      <div className="mb-6">
        <h3 className="text-2xl font-semibold text-gray-800 mb-2">
          Bước 2: Điền thông tin biểu mẫu CT01
        </h3>
        <p className="text-gray-600">
          Các trường có màu xanh đã được tự động điền từ CCCD. Vui lòng bổ sung thông tin còn thiếu.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Debug template */}
        {console.log('🔍 Rendering template fields:', template?.fields)}
        {/* Render fields dynamically from template */}
        {template?.fields?.map((field) => (
          <div key={field.id} className={`form-group ${field.type === 'textarea' ? 'md:col-span-2' : ''}`}>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              {field.label} {field.required && <span className="text-red-500">*</span>}
              {isAutoFilled(field.id) && <span className="text-blue-600 text-xs">(Tự động)</span>}
            </label>
            
            {field.type === 'textarea' ? (
              <textarea
                value={localFormData[field.id] || ''}
                onChange={(e) => handleInputChange(field.id, e.target.value)}
                className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  isAutoFilled(field.id) 
                    ? 'bg-green-50 border-green-300' 
                    : 'border-gray-300'
                }`}
                readOnly={isAutoFilled(field.id)}
                rows={3}
                placeholder={`Nhập ${field.label.toLowerCase()}`}
              />
            ) : field.type === 'select' ? (
              <select
                value={localFormData[field.id] || ''}
                onChange={(e) => handleInputChange(field.id, e.target.value)}
                className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  isAutoFilled(field.id) 
                    ? 'bg-green-50 border-green-300' 
                    : 'border-gray-300'
                }`}
                disabled={isAutoFilled(field.id)}
              >
                <option value="">Chọn...</option>
                {field.options?.map((option) => (
                  <option key={option} value={option}>{option}</option>
                ))}
              </select>
            ) : field.type === 'date' ? (
              <input
                type="date"
                value={localFormData[field.id] || ''}
                onChange={(e) => handleInputChange(field.id, e.target.value)}
                className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  isAutoFilled(field.id) 
                    ? 'bg-green-50 border-green-300' 
                    : 'border-gray-300'
                }`}
                readOnly={isAutoFilled(field.id)}
              />
            ) : field.type === 'number' ? (
              <input
                type="number"
                value={localFormData[field.id] || ''}
                onChange={(e) => handleInputChange(field.id, e.target.value)}
                className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  isAutoFilled(field.id) 
                    ? 'bg-green-50 border-green-300' 
                    : 'border-gray-300'
                }`}
                readOnly={isAutoFilled(field.id)}
              />
            ) : field.type === 'email' ? (
              <input
                type="email"
                value={localFormData[field.id] || ''}
                onChange={(e) => handleInputChange(field.id, e.target.value)}
                className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  isAutoFilled(field.id) 
                    ? 'bg-green-50 border-green-300' 
                    : 'border-gray-300'
                }`}
                readOnly={isAutoFilled(field.id)}
                placeholder={`Nhập ${field.label.toLowerCase()}`}
              />
            ) : field.type === 'table' ? (
              <div className="border border-gray-300 rounded-lg p-4">
                <p className="text-sm text-gray-600 mb-2">Bảng {field.label}</p>
                <div className="overflow-x-auto">
                  <table className="min-w-full border border-gray-300">
                    <thead>
                      <tr className="bg-gray-50">
                        {field.columns?.map((col) => (
                          <th key={col.id} className="border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700">
                            {col.label}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        {field.columns?.map((col) => (
                          <td key={col.id} className="border border-gray-300 px-3 py-2">
                            <input
                              type={col.type === 'date' ? 'date' : col.type === 'number' ? 'number' : 'text'}
                              className="w-full border-none focus:outline-none"
                              placeholder={col.label}
                            />
                          </td>
                        ))}
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            ) : (
              <input
                type="text"
                value={localFormData[field.id] || ''}
                onChange={(e) => handleInputChange(field.id, e.target.value)}
                className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  isAutoFilled(field.id) 
                    ? 'bg-green-50 border-green-300' 
                    : 'border-gray-300'
                }`}
                readOnly={isAutoFilled(field.id)}
                placeholder={`Nhập ${field.label.toLowerCase()}`}
              />
            )}
          </div>
        ))}
      </div>

    </div>
  );
});

export default CT01Form; 