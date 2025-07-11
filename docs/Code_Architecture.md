# 🏗️ Kiến Trúc Code Chi Tiết - Legal Assistant Chatbot

## 🖥️ Tech Stack Sử Dụng

| Layer      | Thành phần chính                                                                 |
|------------|---------------------------------------------------------------------------------|
| **Backend**| Python 3.11, FastAPI, LangGraph, Qdrant, Supabase, SentenceTransformers, LangChain, LlamaGuard, BARTpho, BGE Reranker, AWS Bedrock |
| **Frontend**| React 18, TailwindCSS, React Markdown, Lucide React, Axios                      |
| **DevOps & Services** | Docker, Docker Compose, Nginx, Supabase, Pre-commit, Ruff, ESLint, GitHub Actions (nếu có) |

## 📋 Tổng Quan Hệ Thống

Hệ thống Legal Assistant Chatbot là một ứng dụng AI-powered được xây dựng để hỗ trợ người dùng tìm hiểu về luật pháp Việt Nam. Hệ thống sử dụng kiến trúc microservices với frontend React và backend FastAPI, tích hợp LangGraph để xử lý workflow phức tạp và AWS Bedrock để tương tác với các mô hình ngôn ngữ lớn.

## 🎯 Chức Năng Chính

### 1. Chatbot Thông Minh
- **Tương tác tự nhiên**: Người dùng có thể đặt câu hỏi bằng tiếng Việt về luật pháp, thủ tục hành chính, biểu mẫu, và các vấn đề pháp lý khác
- **Trả lời chính xác**: Hệ thống tìm kiếm và trích xuất thông tin từ cơ sở dữ liệu pháp luật được vector hóa
- **Streaming response**: Trả lời real-time từng phần để tạo trải nghiệm mượt mà

### 2. Tìm Kiếm Thông Minh
- **Semantic search**: Tìm kiếm dựa trên ý nghĩa thay vì từ khóa chính xác
- **Intent classification**: Tự động phân loại loại câu hỏi (luật, biểu mẫu, thủ tục, thuật ngữ)
- **Context-aware**: Hiểu ngữ cảnh từ lịch sử hội thoại để trả lời chính xác hơn

### 3. Quản Lý Tài Liệu
- **Vector database**: Lưu trữ và tìm kiếm hiệu quả các tài liệu pháp luật
- **File download**: Cho phép tải về các biểu mẫu và tài liệu liên quan
- **Source tracking**: Hiển thị nguồn tham khảo rõ ràng cho mỗi câu trả lời

## 🔄 Logic Xử Lý Chính

### 1. Luồng Xử Lý Câu Hỏi

Khi người dùng gửi một câu hỏi, hệ thống thực hiện các bước sau:

#### Bước 1: Phân Loại Intent
Hệ thống đầu tiên phân tích câu hỏi để xác định loại thông tin người dùng đang tìm kiếm:
- **Law**: Câu hỏi về luật pháp, văn bản pháp luật
- **Form**: Câu hỏi về biểu mẫu, giấy tờ hành chính
- **Procedure**: Câu hỏi về thủ tục hành chính
- **Term**: Câu hỏi về thuật ngữ, định nghĩa pháp lý
- **Template**: Câu hỏi về mẫu văn bản
- **Ambiguous**: Câu hỏi không rõ ràng, cần tìm kiếm tổng quát

Việc phân loại này giúp hệ thống chọn đúng cơ sở dữ liệu để tìm kiếm và tạo prompt phù hợp.

#### Bước 2: Kiểm Tra Cache
Hệ thống kiểm tra xem câu hỏi tương tự đã được xử lý trước đó chưa bằng cách so sánh embedding vector. Nếu tìm thấy kết quả cache, hệ thống trả về ngay lập tức để tiết kiệm thời gian và tài nguyên.

#### Bước 3: Kiểm Duyệt An Toàn
Trước khi xử lý, hệ thống kiểm tra tính an toàn của câu hỏi bằng LlamaGuard để đảm bảo không vi phạm các chính sách về nội dung. Nếu câu hỏi bị chặn, hệ thống trả về thông báo an toàn.

#### Bước 4: Cải Thiện Câu Hỏi
Hệ thống sử dụng context từ lịch sử hội thoại để cải thiện câu hỏi, làm cho nó rõ ràng và cụ thể hơn. Ví dụ, nếu người dùng hỏi "Làm thế nào?" sau khi đã hỏi về thủ tục đăng ký thường trú, hệ thống sẽ hiểu rằng họ đang hỏi về cách thực hiện thủ tục đó.

#### Bước 5: Tìm Kiếm Thông Tin
Dựa trên intent đã phân loại, hệ thống tìm kiếm trong các collection tương ứng:
- **legal_chunks**: Chứa các đoạn văn bản pháp luật
- **form_chunks**: Chứa thông tin về biểu mẫu
- **procedure_chunks**: Chứa thông tin về thủ tục hành chính
- **term_chunks**: Chứa định nghĩa thuật ngữ
- **template_chunks**: Chứa mẫu văn bản

Hệ thống sử dụng semantic search để tìm các tài liệu liên quan nhất, sau đó sử dụng reranker để sắp xếp lại kết quả theo độ phù hợp.

#### Bước 6: Tạo Câu Trả Lời
Hệ thống tạo một prompt động dựa trên:
- Loại intent
- Thông tin từ các tài liệu tìm được
- Ngữ cảnh từ lịch sử hội thoại

Prompt này được gửi đến AWS Bedrock (Claude hoặc Llama) để tạo câu trả lời. Hệ thống stream kết quả về frontend để hiển thị real-time.

#### Bước 7: Kiểm Duyệt Đầu Ra
Sau khi tạo câu trả lời, hệ thống kiểm tra tính an toàn của nội dung trả lời để đảm bảo không chứa thông tin nhạy cảm hoặc không phù hợp.

#### Bước 8: Lưu Trữ Lịch Sử
Cuối cùng, hệ thống lưu toàn bộ cuộc hội thoại vào Supabase để có thể truy xuất lại sau này và cải thiện trải nghiệm người dùng.

### 2. Xử Lý Streaming Response

Hệ thống sử dụng Server-Sent Events (SSE) để stream câu trả lời về frontend:

1. **Backend tạo streaming response**: Sau khi có prompt, backend gọi LLM và stream từng chunk về frontend
2. **Frontend xử lý chunks**: Frontend nhận từng chunk và cập nhật UI real-time
3. **Gửi metadata**: Sau khi stream xong nội dung, backend gửi thông tin sources (nguồn tham khảo, link tải file)
4. **Hiển thị sources**: Frontend hiển thị nút tải file và thông tin nguồn tham khảo

### 3. Quản Lý State và Memory

Hệ thống sử dụng LangGraph để quản lý state phức tạp:
- **ChatState**: Lưu trữ toàn bộ thông tin của một cuộc hội thoại
- **Memory management**: Tự động cập nhật và duy trì context từ lịch sử
- **Session management**: Mỗi phiên chat có ID riêng để theo dõi

## 🏗️ Kiến Trúc Hệ Thống

### 1. Backend Architecture

Backend được xây dựng theo kiến trúc layered với các thành phần chính:

#### API Layer (FastAPI)
- **RESTful endpoints**: Cung cấp API cho frontend
- **Streaming support**: Hỗ trợ streaming response
- **CORS handling**: Cho phép frontend truy cập
- **Error handling**: Xử lý lỗi một cách graceful

#### Workflow Layer (LangGraph)
- **State management**: Quản lý state phức tạp của workflow
- **Node orchestration**: Điều phối các bước xử lý
- **Error recovery**: Khôi phục từ lỗi và retry logic
- **Performance monitoring**: Theo dõi thời gian xử lý từng bước

#### Service Layer
- **LLM Service**: Tương tác với AWS Bedrock
- **Vector Service**: Quản lý Qdrant vector database
- **Cache Service**: Quản lý semantic cache
- **Database Service**: Tương tác với Supabase

#### Agent Layer
- **Intent Detector**: Phân loại loại câu hỏi
- **Query Rewriter**: Cải thiện câu hỏi với context
- **Prompt Manager**: Tạo prompt động
- **Guardrails**: Kiểm duyệt an toàn

### 2. Frontend Architecture

Frontend sử dụng React 18 với các pattern hiện đại:

#### Component Architecture
- **App Component**: Quản lý state tổng thể và routing
- **ChatWindow**: Container chính cho giao diện chat
- **Message**: Hiển thị từng tin nhắn với sources
- **MessageInput**: Input cho người dùng nhập câu hỏi

#### State Management
- **Custom Hooks**: useChatStream quản lý logic chat
- **Local State**: Quản lý UI state (loading, sources visibility)
- **Session Management**: Lưu trữ session ID trong localStorage

#### Streaming Integration
- **Fetch API**: Gọi API streaming
- **Event Source**: Xử lý Server-Sent Events
- **Real-time Updates**: Cập nhật UI theo từng chunk

### 3. Data Architecture

#### Vector Database (Qdrant)
- **Collections**: 5 collections cho các loại tài liệu khác nhau
- **Embeddings**: Sử dụng sentence transformers để tạo vector
- **Filtering**: Hỗ trợ filter phức tạp dựa trên metadata
- **Reranking**: Cải thiện chất lượng kết quả tìm kiếm

#### Relational Database (Supabase)
- **Chat History**: Lưu trữ lịch sử hội thoại
- **User Sessions**: Quản lý phiên người dùng
- **Metadata**: Lưu trữ thông tin bổ sung

#### Cache Layer
- **Semantic Cache**: Cache kết quả dựa trên embedding similarity
- **Performance**: Giảm thời gian phản hồi cho câu hỏi tương tự

## 🔧 Các Tính Năng Kỹ Thuật Nổi Bật

### 1. Intent-Based Routing
Hệ thống tự động phân loại câu hỏi và chọn đúng cơ sở dữ liệu để tìm kiếm, giúp tăng độ chính xác và hiệu suất.

### 2. Context-Aware Processing
Hệ thống hiểu ngữ cảnh từ lịch sử hội thoại để cải thiện câu hỏi và tạo câu trả lời phù hợp hơn.

### 3. Real-time Streaming
Người dùng thấy câu trả lời được tạo từng phần thay vì phải chờ toàn bộ, tạo trải nghiệm mượt mà.

### 4. Safety Guardrails
Hệ thống kiểm tra an toàn cả đầu vào và đầu ra để đảm bảo không vi phạm chính sách nội dung.

### 5. File Download Integration
Tự động phát hiện và cung cấp link tải file khi câu trả lời liên quan đến biểu mẫu.

### 6. Source Attribution
Hiển thị rõ ràng nguồn tham khảo cho mỗi câu trả lời, tăng tính minh bạch và độ tin cậy.

## 📊 Hiệu Suất và Tối Ưu Hóa

### 1. Caching Strategy
- **Semantic Cache**: Cache kết quả dựa trên similarity của embedding
- **Session Cache**: Cache thông tin phiên để giảm database calls
- **Prompt Cache**: Cache các prompt template phổ biến

### 2. Async Processing
- **Non-blocking I/O**: Sử dụng async/await để xử lý bất đồng bộ
- **Concurrent Operations**: Thực hiện song song các tác vụ độc lập
- **Background Tasks**: Xử lý các tác vụ nặng trong background

### 3. Resource Management
- **Connection Pooling**: Quản lý hiệu quả database connections
- **Memory Optimization**: Giới hạn context size và cleanup memory
- **Rate Limiting**: Bảo vệ hệ thống khỏi overload

## 🔒 Bảo Mật và An Toàn

### 1. Input Validation
- **Content Filtering**: Kiểm tra nội dung đầu vào
- **Rate Limiting**: Giới hạn số request từ mỗi user
- **SQL Injection Protection**: Sử dụng parameterized queries

### 2. Output Safety
- **Content Moderation**: Kiểm tra nội dung đầu ra
- **Fallback Messages**: Thông báo an toàn khi phát hiện nội dung không phù hợp
- **Audit Logging**: Ghi log các hoạt động để theo dõi

### 3. Data Protection
- **Encryption**: Mã hóa dữ liệu nhạy cảm
- **Access Control**: Kiểm soát quyền truy cập
- **Data Retention**: Chính sách lưu trữ và xóa dữ liệu

## 🚀 Khả Năng Mở Rộng

### 1. Horizontal Scaling
- **Stateless Design**: Backend không lưu state, có thể scale horizontally
- **Load Balancing**: Có thể thêm load balancer để phân phối traffic
- **Database Sharding**: Có thể chia nhỏ database khi cần

### 2. Modular Architecture
- **Service Separation**: Các service độc lập, có thể deploy riêng biệt
- **Plugin System**: Có thể thêm các agent mới dễ dàng
- **Configuration Management**: Cấu hình linh hoạt cho các môi trường khác nhau

### 3. Monitoring and Observability
- **Performance Metrics**: Theo dõi thời gian xử lý từng bước
- **Error Tracking**: Ghi log và alert khi có lỗi
- **Usage Analytics**: Thống kê sử dụng để cải thiện hệ thống

Hệ thống được thiết kế để có thể xử lý hàng nghìn request đồng thời và có thể mở rộng theo nhu cầu sử dụng thực tế. 