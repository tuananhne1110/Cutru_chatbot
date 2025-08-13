import React, { useEffect, useState } from "react";

const CT01Form = React.forwardRef(
  (
    {
      cccdData = {},
      formData = {},
      onSubmit = () => { },
      onChatMessage = () => { },
      template = { fields: [] },
      showSubmitButton = false, // Tuỳ chọn: hiển thị nút "Gửi" ngay trong form
    },
    ref
  ) => {
    const [localFormData, setLocalFormData] = useState(() => ({ ...formData }));
    const [autoFilledFields, setAutoFilledFields] = useState(new Set());

    // --- Utils ---
    const parseDobToYYYYMMDD = (raw) => {
      if (!raw || typeof raw !== "string") return "";
      // Hỗ trợ cả 2 format phổ biến: DD/MM/YYYY hoặc YYYY-MM-DD
      if (/^\d{2}\/\d{2}\/\d{4}$/.test(raw)) {
        const [dd, mm, yyyy] = raw.split("/");
        return `${yyyy}-${mm.padStart(2, "0")}-${dd.padStart(2, "0")}`;
      }
      if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw;
      return "";
    };

    // Khởi tạo/đồng bộ từ cccdData + formData + template
    useEffect(() => {
      const safeFormData = { ...(formData || {}) };
      const auto = new Set();

      if (cccdData && Object.keys(cccdData).length) {
        if (cccdData.personName) {
          safeFormData.ho_ten = cccdData.personName;
          auto.add("ho_ten");
        }
        if (cccdData.idCode) {
          safeFormData.so_dinh_danh = cccdData.idCode;
          auto.add("so_dinh_danh");
        }
        if (cccdData.dateOfBirth) {
          const dob = parseDobToYYYYMMDD(cccdData.dateOfBirth);
          if (dob) {
            safeFormData.ngay_sinh = dob;
            auto.add("ngay_sinh");
          }
        }
        if (cccdData.gender) {
          safeFormData.gioi_tinh = cccdData.gender;
          auto.add("gioi_tinh");
        }
        if (cccdData.residencePlace) {
          safeFormData.dia_chi = cccdData.residencePlace;
          auto.add("dia_chi");
        }
      }

      setLocalFormData(safeFormData);
      setAutoFilledFields(auto);
    }, [cccdData, formData]);

    // Nếu parent cập nhật formData (ngoài chu kỳ init), merge vào local
    useEffect(() => {
      if (formData && Object.keys(formData).length) {
        setLocalFormData((prev) => ({ ...(prev || {}), ...formData }));
      }
    }, [formData]);

    const isAutoFilled = (fieldId) => autoFilledFields.has(fieldId);

    const handleInputChange = (fieldId, value) => {
      setLocalFormData((prev) => ({ ...(prev || {}), [fieldId]: value }));
    };

    const handleAddArrayItem = (fieldId) => {
      setLocalFormData((prev) => {
        const arr = Array.isArray(prev?.[fieldId]) ? prev[fieldId] : [];
        return { ...(prev || {}), [fieldId]: [...arr, {}] };
      });
    };

    const handleRemoveArrayItem = (fieldId, index) => {
      setLocalFormData((prev) => {
        const arr = Array.isArray(prev?.[fieldId]) ? [...prev[fieldId]] : [];
        arr.splice(index, 1);
        return { ...(prev || {}), [fieldId]: arr };
      });
    };

    const handleArrayItemChange = (fieldId, index, subName, value) => {
      setLocalFormData((prev) => {
        const arr = Array.isArray(prev?.[fieldId]) ? [...prev[fieldId]] : [];
        const row = { ...(arr[index] || {}) };
        row[subName] = value;
        arr[index] = row;
        return { ...(prev || {}), [fieldId]: arr };
      });
    };

    const handleSubmit = () => {
      const fields = Array.isArray(template?.fields) ? template.fields : [];
      const requiredFields = fields.filter((f) => f?.required).map((f) => f.id || f.name);
      const missing = requiredFields.filter((fid) => !localFormData?.[fid]);

      if (missing.length) {
        const labelMap = fields.reduce((acc, f) => {
          const key = f.id || f.name;
          acc[key] = f.label || key;
          return acc;
        }, {});
        const msg = missing.map((m) => labelMap[m] || m).join(", ");
        alert(`⚠️ Vui lòng điền đầy đủ các trường bắt buộc: ${msg}`);
        return;
      }

      onSubmit({ ...(localFormData || {}) });
    };

    // Expose qua ref
    React.useImperativeHandle(ref, () => ({ handleSubmit }));

    // --- Render helpers ---
    const renderControl = (field) => {
      const fieldId = field.id || field.name;
      const commonCls = `w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${isAutoFilled(fieldId) ? "bg-green-50 border-green-300" : "border-gray-300"
        }`;
      const value = localFormData?.[fieldId] ?? "";
      const readOnly = !!isAutoFilled(fieldId);

      switch (field.type) {
        case "textarea":
          return (
            <textarea
              value={value}
              onChange={(e) => handleInputChange(fieldId, e.target.value)}
              className={commonCls}
              readOnly={readOnly}
              rows={3}
              placeholder={`Nhập ${field.label?.toLowerCase() || fieldId}`}
            />
          );
        case "select":
          return (
            <select
              value={value}
              onChange={(e) => handleInputChange(fieldId, e.target.value)}
              className={commonCls}
              disabled={readOnly}
            >
              <option value="">Chọn...</option>
              {(field.options || []).map((opt) => (
                <option key={String(opt)} value={opt}>
                  {String(opt)}
                </option>
              ))}
            </select>
          );
        case "date":
          return (
            <input
              type="date"
              value={value}
              onChange={(e) => handleInputChange(fieldId, e.target.value)}
              className={commonCls}
              readOnly={readOnly}
            />
          );
        case "number":
          return (
            <input
              type="number"
              value={value}
              onChange={(e) => handleInputChange(fieldId, e.target.value)}
              className={commonCls}
              readOnly={readOnly}
            />
          );
        case "email":
          return (
            <input
              type="email"
              value={value}
              onChange={(e) => handleInputChange(fieldId, e.target.value)}
              className={commonCls}
              readOnly={readOnly}
              placeholder={`Nhập ${field.label?.toLowerCase() || fieldId}`}
            />
          );
        case "array":
          return (
            <div className="border border-gray-300 rounded-lg p-4">
              <div className="flex justify-between items-center mb-4">
                <h4 className="text-lg font-medium text-gray-900">{field.label}</h4>
                <button
                  type="button"
                  onClick={() => handleAddArrayItem(fieldId)}
                  className="px-3 py-1 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700"
                >
                  + Thêm thành viên
                </button>
              </div>
              <div className="space-y-3">
                {(localFormData?.[fieldId] || []).map((item, index) => (
                  <div key={index} className="border border-gray-200 rounded-lg p-3 bg-gray-50">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm font-medium text-gray-700">Thành viên {index + 1}</span>
                      <button
                        type="button"
                        onClick={() => handleRemoveArrayItem(fieldId, index)}
                        className="text-red-600 hover:text-red-800 text-sm"
                      >
                        ✕ Xóa
                      </button>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {(field.fields || []).map((sub) => (
                        <div key={sub.name} className="form-group">
                          <label className="block text-sm font-medium text-gray-700 mb-1">{sub.label}</label>
                          {sub.type === "select" ? (
                            <select
                              value={item?.[sub.name] || ""}
                              onChange={(e) => handleArrayItemChange(fieldId, index, sub.name, e.target.value)}
                              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                            >
                              <option value="">Chọn...</option>
                              {(sub.options || []).map((opt) => (
                                <option key={String(opt)} value={opt}>
                                  {String(opt)}
                                </option>
                              ))}
                            </select>
                          ) : sub.type === "date" ? (
                            <input
                              type="date"
                              value={item?.[sub.name] || ""}
                              onChange={(e) => handleArrayItemChange(fieldId, index, sub.name, e.target.value)}
                              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                            />
                          ) : (
                            <input
                              type="text"
                              value={item?.[sub.name] || ""}
                              onChange={(e) => handleArrayItemChange(fieldId, index, sub.name, e.target.value)}
                              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                              placeholder={`Nhập ${sub.label?.toLowerCase() || sub.name}`}
                            />
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
                {!(localFormData?.[fieldId] || []).length && (
                  <div className="text-center py-4 text-gray-500">
                    Chưa có thành viên nào. Nhấn "Thêm thành viên" để bắt đầu.
                  </div>
                )}
              </div>
            </div>
          );
        case "table":
          return (
            <div className="border border-gray-300 rounded-lg p-4">
              <div className="flex justify-between items-center mb-4">
                <h4 className="text-lg font-medium text-gray-900">{field.label}</h4>
                <button
                  type="button"
                  onClick={() => handleAddArrayItem(fieldId)}
                  className="px-3 py-1 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700"
                >
                  + Thêm hàng
                </button>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full border border-gray-300">
                  <thead>
                    <tr className="bg-gray-50">
                      {(field.columns || []).map((col) => (
                        <th
                          key={col.id || col.name}
                          className="border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700"
                        >
                          {col.label}
                        </th>
                      ))}
                      <th className="border border-gray-300 px-3 py-2" />
                    </tr>
                  </thead>
                  <tbody>
                    {(localFormData?.[fieldId] || []).map((row, index) => (
                      <tr key={index}>
                        {(field.columns || []).map((col) => (
                          <td key={col.id || col.name} className="border border-gray-300 px-3 py-2">
                            <input
                              type={col.type === "date" ? "date" : col.type === "number" ? "number" : "text"}
                              value={row?.[col.name] || ""}
                              onChange={(e) => handleArrayItemChange(fieldId, index, col.name, e.target.value)}
                              className="w-full border-none focus:outline-none"
                              placeholder={col.label}
                            />
                          </td>
                        ))}
                        <td className="border border-gray-300 px-3 py-2 text-center">
                          <button
                            type="button"
                            onClick={() => handleRemoveArrayItem(fieldId, index)}
                            className="text-red-600 hover:text-red-800 text-sm"
                          >
                            ✕
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {!(localFormData?.[fieldId] || []).length && (
                <div className="text-center py-4 text-gray-500">
                  Chưa có dữ liệu. Nhấn "Thêm hàng" để bắt đầu.
                </div>
              )}
            </div>
          );
        default:
          return (
            <input
              type="text"
              value={value}
              onChange={(e) => handleInputChange(fieldId, e.target.value)}
              className={commonCls}
              readOnly={readOnly}
              placeholder={`Nhập ${field.label?.toLowerCase() || fieldId}`}
            />
          );
      }
    };

    const fields = Array.isArray(template?.fields) ? template.fields : [];

    return (
      <div>
        <div className="mb-6">
          <h3 className="text-2xl font-semibold text-gray-800 mb-2">Bước 2: Điền thông tin biểu mẫu CT01</h3>
          <p className="text-gray-600">
            Các trường có màu xanh đã được tự động điền từ CCCD. Vui lòng bổ sung thông tin còn thiếu.
          </p>
        </div>

        {!fields.length ? (
          <div className="p-4 rounded-lg border border-amber-300 bg-amber-50 text-amber-800">
            Chưa có cấu hình trường biểu mẫu (template.fields trống).
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {fields.map((field) => {
              const fieldId = field.id || field.name;
              return (
                <div
                  key={fieldId}
                  className={`form-group ${field.type === "textarea" ? "md:col-span-2" : ""}`}
                >
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    {field.label} {field.required && <span className="text-red-500">*</span>}
                    {isAutoFilled(fieldId) && <span className="text-blue-600 text-xs"> (Tự động)</span>}
                  </label>
                  {renderControl(field)}
                </div>
              );
            })}
          </div>
        )}

        {showSubmitButton && (
          <div className="mt-8">
            <button
              type="button"
              onClick={handleSubmit}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Gửi biểu mẫu
            </button>
          </div>
        )}
      </div>
    );
  }
);

export default CT01Form;