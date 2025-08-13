import React from 'react';
import ReactMarkdown from 'react-markdown';

function Message({ message, showSources, toggleSources }) {
  return (
    <div className={`mb-3 flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm leading-relaxed ${
        message.type === 'user'
          ? 'bg-gradient-to-br from-blue-500 to-purple-600 text-white'
          : message.type === 'error'
          ? 'bg-red-100 text-red-800'
          : 'bg-white text-gray-900 border border-gray-200'
      }`}>
        <div className="flex items-start space-x-2">
          <div className="flex-1">
            <div className="prose prose-sm max-w-none text-sm">
              {/* Loại bỏ hoặc thay thế link file trong nội dung trả lời */}
              {(() => {
                const fileUrlRegex = /https?:\/\/\S+\.(docx?|pdf|xlsx?|zip|rar)(\?\S*)?/gi;
                // Thay thế link file bằng thông báo ngắn gọn
                const contentWithoutLinks = message.content.replace(fileUrlRegex, '[📥 Tải về mẫu ở phía dưới]');
                return <ReactMarkdown>{contentWithoutLinks}</ReactMarkdown>;
              })()}
            </div>
            {/* Nút tải file nếu có file_url hoặc url hợp lệ trong sources */}
            {message.sources && message.sources.length > 0 && (() => {
              // Chỉ lấy file đầu tiên có file_url hợp lệ
              const firstDownloadable = message.sources.find(
                source => (source.file_url || source.url || '').match(/\.(docx?|pdf|xlsx?|zip|rar)(\?.*)?$/i)
              );
              if (firstDownloadable) {
                const fileUrl = firstDownloadable.file_url || firstDownloadable.url;
                const fileName =
                  firstDownloadable.code
                    ? `mau_${firstDownloadable.code}.docx`
                    : firstDownloadable.title
                    ? firstDownloadable.title.replace(/\s+/g, '_') + '.docx'
                    : fileUrl.split('/').pop()?.split('?')[0] || 'downloaded_file';
                return (
                  <div className="mt-2">
                    <a
                      href={fileUrl}
                      download={fileName}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-block px-2 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 text-xs font-semibold shadow underline"
                      style={{ textDecoration: 'underline', cursor: 'pointer' }}
                    >
                      📥 Tải về {firstDownloadable.code ? `mẫu ${firstDownloadable.code}` : fileName}
                    </a>
                  </div>
                );
              }
              return null;
            })()}
            {message.sources && message.sources.length > 0 && (
              <div className="mt-2">
                <button
                  onClick={() => toggleSources(message.id)}
                  className="text-xs text-blue-600 hover:text-blue-800 flex items-center space-x-1"
                >
                  <span role="img" aria-label="book">📖</span>
                  <span>
                    {showSources[message.id] ? 'Ẩn' : 'Hiện'} nguồn ({message.sources.length})
                  </span>
                </button>
                {showSources[message.id] && (
                  <div className="mt-1 space-y-1">
                    {message.sources.map((source, index) => (
                      <div key={index} className="text-xs bg-blue-50 p-1 rounded">
                        {/* Nếu là nguồn luật */}
                        {source.law_name && (
                          <>
                        <div className="font-medium">{source.law_name}</div>
                        {source.law_code && <div>Mã: {source.law_code}</div>}
                        {source.chapter && <div>Chương: {source.chapter}</div>}
                        {source.chapter_content && <div>Nội dung chương: {source.chapter_content}</div>}
                          </>
                        )}
                        {/* Nếu là nguồn biểu mẫu */}
                        {source.title && (
                          <>
                            <div className="font-medium">{source.title} {source.code && <span>({source.code})</span>}</div>
                            {source.file_url && (
                              <a
                                href={source.file_url}
                                download={source.code ? `mau_${source.code}.docx` : undefined}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-blue-600 underline"
                              >
                                📥 Tải về
                              </a>
                            )}
                          </>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
            <div className="text-xs opacity-70 mt-1">
              {new Date(message.timestamp).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Message; 