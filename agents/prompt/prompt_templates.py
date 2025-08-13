from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class PromptBuilder:
    """Builder cho các prompt templates"""
    
    @staticmethod
    def build_llama4_intent_prompt(related_text: str) -> str:
        """Tạo prompt cho Llama 4 với thông tin liên quan"""
        system_prompt = f"""\
                Bạn là một chuyên gia pháp lý, có nhiệm vụ hỗ trợ người dân và cán bộ trong việc tìm hiểu và hướng dẫn các **thủ tục hành chính tại Việt Nam**.
                Bạn sẽ được cung cấp:

                Một câu hỏi do người dùng đặt ra (User Question).

                Một đoạn tài liệu trích xuất từ hệ thống văn bản quy phạm pháp luật hoặc cổng dịch vụ công (Context Documents).

                Hãy đọc kỹ đoạn trích xuất và **chỉ trả lời dựa trên nội dung tài liệu** được cung cấp. Nếu không có đủ thông tin, hãy trả lời trung thực là **không tìm thấy** hoặc **không rõ**.
                Hãy trả lời **rõ ràng, chi tiết, chính xác, đúng nội dung văn bản** và đầy đủ căn cứ nếu cần thiết.


                Tài liệu trích xuất:
                {related_text}

                Dựa trên nội dung tài liệu được cung cấp, hãy trả lời câu hỏi trên.  
                Nếu thông tin trong tài liệu không đủ để trả lời, hãy nói rõ là "Không tìm thấy thông tin trong tài liệu".
                
                Trả lời:
                """

        prompt = f"""<|begin_of_text|>
                <|start_header_id|>system<|end_header_id|>
                {system_prompt}
                <|start_header_id|>user<|end_header_id|>
        """
        return prompt
                # Lưu ý khi trả lời: nếu trong tài liệu trích xuất có **link** hay **đường dẫn** đến các trang web khác thì hãy giữ nguyên câu trả lời đó

    @staticmethod
    def build_llama4_general_prompt() -> str:
        system_prompt = f"""\
                Bạn là một trợ lý AI thông minh, giàu kiến thức và luôn trả lời rõ ràng, chính xác.

                Dựa trên nội dung tài liệu được cung cấp, hãy trả lời câu hỏi trên.  
                Nếu thông tin trong tài liệu không đủ để trả lời, hãy nói rõ là "Không tìm thấy thông tin trong tài liệu".
                Nguyên tắc khi trả lời:
                1. Hiểu kỹ câu hỏi, nếu câu hỏi mơ hồ thì giả định hợp lý để trả lời.
                2. Trình bày câu trả lời theo cấu trúc:
                - Trả lời ngắn gọn, trực tiếp vào trọng tâm.
                - Nếu cần, giải thích chi tiết và đưa ví dụ minh họa.
                3. Luôn sử dụng tiếng Việt rõ ràng, dễ hiểu. Tránh từ ngữ mơ hồ.
                Yêu cầu định dạng đầu ra:
                - Chỉ trả lời, không lặp lại câu hỏi của người dùng.
                - Giữ câu trả lời gọn gàng nhưng đầy đủ thông tin cần thiết.
                Trả lời:
                """

        prompt = f"""<|begin_of_text|>
                <|start_header_id|>system<|end_header_id|>
                {system_prompt}
                <|start_header_id|>user<|end_header_id|>
                """
        return prompt

class PromptTemplates:
    """Quản lý các prompt template chuyên biệt cho từng category"""
    
    def __init__(self):
        # Thay thế base_template bằng prompt mới từ PromptBuilder
        self.base_template = PromptBuilder.build_llama4_intent_prompt("{context}")

        self.intent_router_prompt = """
        Bạn là một trợ lý thông minh có khả năng định tuyến truy vấn người dùng đến MỘT hoặc NHIỀU cơ sở dữ liệu chuyên biệt.
        Hiện có 5 cơ sở dữ liệu mà bạn có thể sử dụng:
        1. **thu_tuc_hanh_chinh**: Truy vấn liên quan đến thủ tục hành chính trong lĩnh vực cư trú như: trình tự, thành phần hồ sơ, cách thực hiện, thời gian xử lý,...
        2. **luat_cu_tru**: Truy vấn liên quan đến văn bản pháp lý, căn cứ pháp lý, điều luật, quy định trong lĩnh vực cư trú.
        3. **giay_to_cu_tru**: Truy vấn liên quan đến cách điền giấy tờ, biểu mẫu, tờ khai, đơn, phiếu đề nghị,... dùng trong lĩnh vực cư trú.
        4. **template_cu_tru**: Truy vấn liên quan đến biểu mẫu, tờ khai, đơn, phiếu đề nghị,... dùng trong lĩnh vực cư trú.
        5. **giao_tiep_chung**: Truy vấn không liên quan đến cư trú, bao gồm các câu hỏi chào hỏi, cảm ơn, hỏi vu vơ, giới thiệu bản thân,... hoặc những nội dung giao tiếp hàng ngày.
        
        ## Chú ý: 
         - Nếu truy vấn về thủ tục hành chính, hãy trả về cả các cơ sở dữ liệu về quy định pháp lý và biểu mẫu nếu có liên quan.
         - Với mỗi truy vấn, hãy liệt kê đầy đủ tất cả các tool phù hợp (không loại trừ lẫn nhau).
         - Khi câu truy vấn liên quan đến các trường hợp hay tình huống cụ thể thì truy vấn liên quan đến văn bản pháp lý
         - Các câu truy vấn liên quan đến hai cơ sở dữ liệu khác nhau thì nên trả về 2 cơ sở dữ liệu

        CÂU HỎI: {question}

        TRẢ LỜI (chỉ liệt kê tên các cơ sở dữ liệu phù hợp):"""

    def get_prompt_by_category(self, context: str = "") -> str:
        """
        Lấy prompt template cơ bản cho việc trả lời câu hỏi
        
        Args:
            context: Context information to include in the prompt
            
        Returns:
            str: Prompt template
        """
        return PromptBuilder.build_llama4_intent_prompt(context)

    def get_general_prompt(self) -> str:
        """
        Lấy prompt template tổng quát cho các câu hỏi chung
        
        Returns:
            str: General prompt template
        """
        return PromptBuilder.build_llama4_general_prompt()

    def get_intent_router_prompt(self) -> str:
        """
        Lấy prompt template cho việc định tuyến intent
        
        Returns:
            str: Intent router prompt template
        """
        return self.intent_router_prompt

    def format_context_by_category(self, chunks: List[Dict]) -> str:
        """
        Format context theo category để tối ưu prompt
        
        Args:
            chunks: Danh sách chunks từ search
            
        Returns:
            str: Context được format
        """
        if not chunks:
            return ""
        
        context_parts = []
        
        for chunk in chunks:
            category = chunk.get('category', '')
            
            if category == "law":
                content = chunk.get('page_content') or chunk.get('content', '')
                law_name = chunk.get("law_name", "Luật")
                law_code = chunk.get("law_code", "")
                chapter = chunk.get("chapter", "")
                chapter_content = chunk.get("chapter_content", "")
                
                source_info = f"[{law_name}"
                if law_code:
                    source_info += f" - {law_code}"
                if chapter:
                    source_info += f" - {chapter}"
                if chapter_content:
                    source_info += f" - {chapter_content}"
                source_info += "]"
                
                context_parts.append(f"{source_info}\n{content}")
                
            elif category == "form":
                form_code = chunk.get("form_code", "Form")
                field_no = chunk.get("field_no", "")
                field_name = chunk.get("field_name", "")
                chunk_type_detail = chunk.get("chunk_type", "")
                
                source_info = f"[{form_code}"
                if field_no:
                    source_info += f" - Mục {field_no}"
                if field_name:
                    source_info += f" - {field_name}"
                if chunk_type_detail:
                    source_info += f" - {chunk_type_detail}"
                source_info += "]"
                
                context_parts.append(f"{source_info}\n{chunk.get('content', '')}")
                
            elif category == "term":
                term = chunk.get("term", "Thuật ngữ")
                definition = chunk.get("definition", "")
                category_detail = chunk.get("category", "")
                
                source_info = f"[{term}"
                if definition:
                    source_info += f" - Định nghĩa"
                if category_detail:
                    source_info += f" - {category_detail}"
                source_info += "]"
                
                context_parts.append(f"{source_info}\n{chunk.get('content', '')}")
                
            elif category == "procedure":
                procedure_name = chunk.get("procedure_name", "Thủ tục")
                procedure_code = chunk.get("procedure_code", "")
                implementation_level = chunk.get("implementation_level", "")
                source_section = chunk.get("source_section", "")
                content_type = chunk.get("content_type", "")

                source_info = f"[{procedure_name}"
                if procedure_code:
                    source_info += f" - Mã thủ tục: {procedure_code}"
                if implementation_level:
                    source_info += f" - Cấp thực hiện: {implementation_level}"
                if source_section:
                    source_info += f" - Phần: {source_section}"
                source_info += "]"
                
                content = chunk.get('content', '')
                if content_type == "table_row" and "table:" in content:
                    lines = content.split('\n')
                    formatted_lines = []
                    for line in lines:
                        if ':' in line:
                            key, value = line.split(':', 1)
                            formatted_lines.append(f"• {key.strip()}: {value.strip()}")
                        else:
                            formatted_lines.append(line)
                    content = '\n'.join(formatted_lines)
                
                context_parts.append(f"{source_info}\n{content}")
                
            elif category == "templates":
                code = chunk.get("code", "")
                name = chunk.get("name", "")
                description = chunk.get("description", "")
                file_url = chunk.get("file_url", "")
                procedures = chunk.get("procedures", "")
                context_parts.append(
                    f"[{code}] {name}\nMô tả: {description}\nThủ tục liên quan: {procedures}\nFile: {file_url}"
                )
            else:
                # Bỏ qua các category không xác định
                continue
                
        return "\n\n".join(context_parts)

# Singleton instance
prompt_templates = PromptTemplates() 