import React, { useState, useEffect } from 'react';
import { ct01Service } from '../services/ct01Service';

function CT01History({ onSelectForm, onClose }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      setLoading(true);
      const data = await ct01Service.getCT01History();
      setHistory(data);
    } catch (err) {
      setError('Không thể tải lịch sử. Vui lòng thử lại.');
      console.error('Error loading CT01 history:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('vi-VN');
  };

  const formatCurrency = (amount) => {
    if (!amount) return '0';
    return new Intl.NumberFormat('vi-VN').format(amount);
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return 'text-green-600 bg-green-100';
      case 'draft':
        return 'text-yellow-600 bg-yellow-100';
      case 'submitted':
        return 'text-blue-600 bg-blue-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'completed':
        return 'Hoàn tất';
      case 'draft':
        return 'Bản nháp';
      case 'submitted':
        return 'Đã nộp';
      default:
        return 'Không xác định';
    }
  };

  if (loading) {
    return (
      <div className="p-6 text-center">
        <div className="inline-flex items-center space-x-2 text-blue-600">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
          <span>Đang tải lịch sử...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 text-center">
        <div className="text-red-600 mb-4">{error}</div>
        <button
          onClick={loadHistory}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Thử lại
        </button>
      </div>
    );
  }

  if (history.length === 0) {
    return (
      <div className="p-6 text-center">
        <div className="text-gray-500 mb-4">
          <span className="text-4xl block mb-2">📋</span>
          <p>Chưa có biểu mẫu CT01 nào</p>
        </div>
        <button
          onClick={onClose}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Tạo mới
        </button>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-xl font-semibold text-gray-800">Lịch sử biểu mẫu CT01</h3>
        <button
          onClick={onClose}
          className="text-gray-500 hover:text-gray-700"
        >
          ✕
        </button>
      </div>

      <div className="space-y-4 max-h-96 overflow-y-auto">
        {history.map((form) => (
          <div
            key={form.id}
            className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
            onClick={() => onSelectForm(form)}
          >
            <div className="flex justify-between items-start mb-2">
              <div>
                <h4 className="font-semibold text-gray-800">
                  {form.ho_ten || 'Không có tên'}
                </h4>
                <p className="text-sm text-gray-600">
                  CCCD: {form.so_cccd || 'N/A'}
                </p>
              </div>
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(form.status)}`}>
                {getStatusText(form.status)}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-500">Thu nhập:</span>
                <span className="ml-2 font-medium">{formatCurrency(form.thu_nhap)} VNĐ</span>
              </div>
              <div>
                <span className="text-gray-500">Ngày tạo:</span>
                <span className="ml-2">{formatDate(form.created_at)}</span>
              </div>
            </div>

            {form.reference_id && (
              <div className="mt-2 text-xs text-gray-500">
                Mã tham chiếu: {form.reference_id}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="mt-6 text-center">
        <button
          onClick={onClose}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Tạo biểu mẫu mới
        </button>
      </div>
    </div>
  );
}

export default CT01History; 