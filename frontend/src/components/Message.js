import React from 'react';
import ReactMarkdown from 'react-markdown';

function Message({ message, showSources, toggleSources }) {
  return (
    <div className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[80%] rounded-lg p-3 ${
        message.type === 'user'
          ? 'bg-blue-600 text-white'
          : message.type === 'error'
          ? 'bg-red-100 text-red-800'
          : 'bg-gray-100 text-gray-900'
      }`}>
        <div className="flex items-start space-x-2">
          <div className="flex-1">
            <div className="prose prose-sm max-w-none">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
            {message.sources && message.sources.length > 0 && (
              <div className="mt-3">
                <button
                  onClick={() => toggleSources(message.id)}
                  className="text-xs text-blue-600 hover:text-blue-800 flex items-center space-x-1"
                >
                  <span role="img" aria-label="book">📖</span>
                  <span>
                    {showSources[message.id] ? 'Ẩn' : 'Hiện'} nguồn tham khảo ({message.sources.length})
                  </span>
                </button>
                {showSources[message.id] && (
                  <div className="mt-2 space-y-1">
                    {message.sources.map((source, index) => (
                      <div key={index} className="text-xs bg-blue-50 p-2 rounded">
                        <div className="font-medium">{source.law_name}</div>
                        {source.article && <div>{source.article}</div>}
                        {source.chapter && <div>Chương: {source.chapter}</div>}
                        {source.clause && <div>Khoản: {source.clause}</div>}
                        {source.point && <div>Điểm: {source.point}</div>}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
            <div className="text-xs opacity-70 mt-2">
              {new Date(message.timestamp).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Message; 