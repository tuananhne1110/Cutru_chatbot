import React from 'react';

function VoiceRecorder({ 
  isRecording, 
  voiceLoading, 
  voiceError, 
  onToggleRecording, 
  onStopRecording 
}) {
  const handleClick = (e) => {
    e.preventDefault();
    e.stopPropagation();
    onToggleRecording();
  };

  return (
    <div className="mb-2">
      <button
        onClick={handleClick}
        disabled={voiceLoading}
        className={`
          w-full px-4 py-2 rounded-lg border text-sm font-medium transition-all
          ${isRecording 
            ? 'bg-red-500 text-white border-red-500 hover:bg-red-600' 
            : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
          }
          ${voiceLoading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        `}
        title={isRecording ? "Nhấn để dừng ghi âm" : "Nhấn để bắt đầu ghi âm"}
      >
        {voiceLoading ? (
          <span className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current mr-2"></div>
            Đang xử lý...
          </span>
        ) : isRecording ? (
          <span className="flex items-center justify-center">
            <div className="w-2 h-2 bg-white rounded-full mr-2 animate-pulse"></div>
            🎤 Đang ghi âm - Nhấn để dừng
          </span>
        ) : (
          <span className="flex items-center justify-center">
            🎤 Nhấn để ghi âm giọng nói
          </span>
        )}
      </button>
      
      {voiceError && (
        <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-red-600 text-sm">
          ❌ {voiceError}
        </div>
      )}
    </div>
  );
}

export default VoiceRecorder;
