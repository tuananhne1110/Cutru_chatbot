import React, { useState } from 'react';

function CCCDScanner({ onScanned, onChatMessage }) {
  const [isScanning, setIsScanning] = useState(false);
  const [scanResult, setScanResult] = useState(null);

  const startScan = async () => {
    setIsScanning(true);
    
    try {
      // Simulate scanning process
      await new Promise(resolve => setTimeout(resolve, 2500));
      
      // TODO: Implement real CCCD scanning
      // For now, return empty data - user will need to manually enter
      const emptyCCCDData = {
        idCode: '',
        oldIdCode: '',
        personName: '',
        dateOfBirth: '',
        gender: '',
        nationality: 'Việt Nam',
        race: '',
        religion: '',
        originPlace: '',
        residencePlace: '',
        personalIdentification: '',
        issueDate: '',
        expiryDate: '',
        wifeName: '',
        fatherName: '',
        motherName: '',
        qr: ''
      };
      
      setScanResult(emptyCCCDData);
      onScanned(emptyCCCDData);
    } catch (error) {
      console.error('Scanning error:', error);
    } finally {
      setIsScanning(false);
    }
  };

  const importFile = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.txt,.json,.xml,.pdf';
    input.onchange = async (e) => {
      if (e.target.files[0]) {
        setIsScanning(true);
        
        try {
          // Simulate file processing
          await new Promise(resolve => setTimeout(resolve, 1000));
          
          // TODO: Implement real file parsing
          // For now, return empty data - user will need to manually enter
          const emptyCCCDData = {
            idCode: '',
            oldIdCode: '',
            personName: '',
            dateOfBirth: '',
            gender: '',
            nationality: 'Việt Nam',
            race: '',
            religion: '',
            originPlace: '',
            residencePlace: '',
            personalIdentification: '',
            issueDate: '',
            expiryDate: '',
            wifeName: '',
            fatherName: '',
            motherName: '',
            qr: ''
          };
          
          setScanResult(emptyCCCDData);
          onScanned(emptyCCCDData);
        } catch (error) {
          console.error('File processing error:', error);
        } finally {
          setIsScanning(false);
        }
      }
    };
    input.click();
  };

  return (
    <div className="text-center py-8">
      <div className="mb-8">
        <h3 className="text-2xl font-semibold text-gray-800 mb-2">
          Bước 1: Quét thẻ căn cước công dân
        </h3>
        <p className="text-gray-600">
          Đặt thẻ CCCD lên đầu đọc hoặc tải lên file dữ liệu để tự động trích xuất thông tin
        </p>
      </div>

      <div className="mb-8">
        <div className="w-32 h-32 bg-gradient-to-br from-blue-400 to-blue-600 rounded-full flex items-center justify-center mx-auto mb-6">
          <span className="text-4xl">📇</span>
        </div>
        <h4 className="text-lg font-medium text-gray-700 mb-2">
          Sẵn sàng quét thẻ CCCD
        </h4>
        <p className="text-gray-500">
          Vui lòng đặt thẻ căn cước lên đầu đọc để bắt đầu
        </p>
      </div>

      <div className="flex justify-center space-x-4 mb-8">
        <button
          onClick={startScan}
          disabled={isScanning}
          className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isScanning ? '⏳ Đang quét...' : '🔍 Bắt đầu quét'}
        </button>
        <button
          onClick={importFile}
          disabled={isScanning}
          className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          📁 Tải file lên
        </button>
      </div>

      {scanResult && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-6 text-left">
          <div className="flex items-center mb-4">
            <span className="text-2xl mr-3">✅</span>
            <div>
              <h5 className="text-green-800 font-semibold">Quét thành công!</h5>
              <span className="text-green-600 text-sm">17 trường dữ liệu</span>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="bg-white p-3 rounded border">
              <div className="text-sm font-medium text-gray-600">Số định danh</div>
              <div className="text-gray-800">{scanResult.idCode}</div>
            </div>
            <div className="bg-white p-3 rounded border">
              <div className="text-sm font-medium text-gray-600">Họ và tên</div>
              <div className="text-gray-800">{scanResult.personName}</div>
            </div>
            <div className="bg-white p-3 rounded border">
              <div className="text-sm font-medium text-gray-600">Ngày sinh</div>
              <div className="text-gray-800">{scanResult.dateOfBirth}</div>
            </div>
            <div className="bg-white p-3 rounded border">
              <div className="text-sm font-medium text-gray-600">Giới tính</div>
              <div className="text-gray-800">{scanResult.gender}</div>
            </div>
            <div className="bg-white p-3 rounded border">
              <div className="text-sm font-medium text-gray-600">Quốc tịch</div>
              <div className="text-gray-800">{scanResult.nationality}</div>
            </div>
            <div className="bg-white p-3 rounded border md:col-span-2 lg:col-span-3">
              <div className="text-sm font-medium text-gray-600">Nơi thường trú</div>
              <div className="text-gray-800">{scanResult.residencePlace}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default CCCDScanner; 