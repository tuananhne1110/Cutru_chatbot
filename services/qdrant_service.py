import sys
import os
from app_config import qdrant_client
import instructor
import google.generativeai as genai
from instructor import Mode
from pydantic import BaseModel
from dotenv import load_dotenv
from qdrant_client.models import Filter, Condition

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY")) # type: ignore

gemini_model = genai.GenerativeModel("gemini-1.5-flash-latest") # type: ignore
llm_client = instructor.from_gemini(
    client=gemini_model,
    mode=Mode.GEMINI_JSON
)

class QdrantFilterWrapper(BaseModel):
    must: list[Condition] = []
    must_not: list[Condition] = []
    should: list[Condition] = []

    def to_qdrant_filter(self) -> Filter:
        return Filter(
            must=self.must if self.must else None,
            must_not=self.must_not if self.must_not else None,
            should=self.should if self.should else None
        )

FILTER_PROMPT_PROCEDURE = """
Bạn là một trợ lý AI có nhiệm vụ trích xuất bộ lọc từ truy vấn tiếng Việt để phục vụ tìm kiếm thủ tục hành chính.

Vui lòng tuân thủ các quy tắc sau:
1. Truy vấn được đặt trong thẻ <query>...</query>.
2. Danh sách các trường cho phép lọc sẽ được cung cấp trong thẻ <indexes>...</indexes>.
3. Chỉ sử dụng các trường có trong <indexes>. Không tự tạo thêm trường mới.
4. Chỉ sinh filter nếu bạn chắc chắn rằng ý định của người dùng tương ứng với tên trường và giá trị hợp lệ.
5. Không nên suy đoán. Nếu không tìm được trường phù hợp, hãy trả về bộ lọc rỗng.
6. Nếu người dùng đề cập đến điều gì đó cần loại trừ, hãy đưa vào mục `must_not`.
7. Nếu truy vấn có chứa nhiều điều kiện, hãy kết hợp tất cả trong `must` (và `must_not` nếu có loại trừ).
8. Không cần sử dụng `should` và `min_should` trừ khi thực sự cần thiết.
9. Giải thích các trường có trong <indexes> để đảm bảo hiểu đúng ý định của người dùng.
   - **procedure_code** (`KEYWORD`): Mã số thủ tục hành chính. VD: `"1.002755"`.
   - **category** (`KEYWORD`): Nhóm nội dung. Thường là `"Thủ tục hành chính"`.
   - **content_type** (`KEYWORD`): Loại nội dung: `"text"` hoặc `"table_row"`.
   - **implementing_agency** (`KEYWORD`): Cơ quan trực tiếp xử lý. VD: `"Công an Xã"`.
   - **implementation_subject** (`KEYWORD`): Đối tượng thực hiện. VD: `"Công dân Việt Nam"`, `"Tổ chức"`.
   - **coordinating_agency** (`KEYWORD`): Cơ quan phối hợp thực hiện (nếu có).
   - **implementation_result** (`KEYWORD`): Kết quả xử lý. VD: `"Cập nhật dữ liệu cư trú"`.
   - **implementation_level** (`KEYWORD`): Cấp thực hiện. VD: `"Cấp Xã"`, `"Cấp Huyện"`.
   - **procedure_name** (`KEYWORD`): Tên thủ tục. VD: `"Gia hạn tạm trú"`, "Đăng ký tạm trú"`
   - **competent_authority** (`KEYWORD`): Cơ quan có thẩm quyền quyết định.
   - **field** (`KEYWORD`): Lĩnh vực quản lý. VD: `"Cư trú"`, `"Xuất nhập cảnh"`.
   - **application_receiving_address** (`KEYWORD`): Địa điểm tiếp nhận hồ sơ.
   - **procedure_type** (`KEYWORD`): Loại thủ tục. VD: `"TTHC được luật giao quy định chi tiết"`.
   - **source_section** (`KEYWORD`): Phần nội dung gốc, chỉ có trong 4 thành phân `"Trình tự thực hiện"`, `"cách thức thực hiện"`, `"thành phần hồ sơ"` và `"Căn cứ pháp lý"`
   - **decision_number** (`KEYWORD`): Số hiệu quyết định ban hành thủ tục.
   - **authorized_agency** (`KEYWORD`): Cơ quan được ủy quyền thực hiện (nếu có).
   - **table_title** (`KEYWORD`): Tiêu đề của bảng dữ liệu (nếu có). VD: `"Cách thức thực hiện"`.
Luôn ưu tiên độ chính xác hơn số lượng điều kiện lọc. Nếu không chắc chắn, hãy bỏ qua.
"""

FILTER_PROMPT_LEGAL= """
Bạn là một trợ lý AI có nhiệm vụ trích xuất bộ lọc từ truy vấn tiếng Việt để phục vụ tìm kiếm văn bản pháp luật về cư trú.

Vui lòng tuân thủ các quy tắc sau:
1. Truy vấn được đặt trong thẻ <query>...</query>.
2. Danh sách các trường cho phép lọc sẽ được cung cấp trong thẻ <indexes>...</indexes>.
3. Chỉ sử dụng các trường có trong <indexes>. Không tự tạo thêm trường mới.
4. Chỉ sinh filter nếu bạn chắc chắn rằng ý định của người dùng tương ứng với tên trường và giá trị hợp lệ.
5. Không nên suy đoán. Nếu không tìm được trường phù hợp, hãy trả về bộ lọc rỗng.
6. Nếu người dùng đề cập đến điều gì đó cần loại trừ, hãy đưa vào mục `must_not`.
7. Nếu truy vấn có chứa nhiều điều kiện, hãy kết hợp tất cả trong `must` (và `must_not` nếu có loại trừ).
8. Không cần sử dụng `should` và `min_should` trừ khi thực sự cần thiết.
9. Luôn ưu tiên độ chính xác hơn số lượng điều kiện lọc. Nếu không chắc chắn, hãy bỏ qua.
10. Giải thích các trường có trong <indexes> để đảm bảo hiểu đúng ý định của người dùng.
    - **law_name** (`KEYWORD`): Tên đầy đủ của văn bản pháp luật. VD: `"luật xuất nhập cảnh"`.
    - **law_code** (`KEYWORD`): Mã số văn bản pháp luật. VD: `"04/2016/TT-BNG"`.
    - **promulgation_date** (`KEYWORD`): Ngày ban hành văn bản. VD: `"30 tháng 6 năm 2016"`.
    - **effective_date** (`KEYWORD`): Ngày có hiệu lực (nếu có). VD: `"01 tháng 8 năm 2016"`.
    - **promulgator** (`KEYWORD`): Cơ quan ban hành. VD: `"bộ ngoại giao"`, `"chính phủ"`.
    - **law_type** (`KEYWORD`): Loại văn bản. VD: `"thông tư"`, `"nghị định"`, `"luật"`.
    - **chapter** (`KEYWORD`): Chương. VD: `"chương i"`, `"chương ii"`.
    - **section** (`KEYWORD`): Mục (nếu có). VD: `"mục 1"`, `"mục 2"`.
    - **article** (`KEYWORD`): Điều. VD: `"điều 1"`, `"điều 10"`.
    - **clause** (`KEYWORD`): Khoản (nếu có). VD: `"khoản 1"`, `"khoản 2"`.
    - **point** (`KEYWORD`): Điểm (nếu có). VD: `"điểm a"`, `"điểm b"`.
    - **type** (`KEYWORD`): Loại cấu trúc văn bản. VD: `"điều"`, `"khoản"`, `"điểm"`.
    - **id** (`KEYWORD`): Mã định danh duy nhất của đoạn văn bản.
    - **parent_id** (`KEYWORD`): Mã định danh của cấu trúc cha.
    - **parent_type** (`KEYWORD`): Loại cấu trúc cha. VD: `"chương"`, `"điều"`, `"khoản"`.
    - **law_ref** (`KEYWORD`): Tham chiếu đầy đủ của văn bản.
    - **category** (`KEYWORD`): Danh mục. VD: `"law"`.
"""


FILTER_PROMPT_FROM = """
Bạn là một trợ lý AI có nhiệm vụ trích xuất bộ lọc từ truy vấn tiếng Việt để phục vụ tìm kiếm giấy tờ và biểu mẫu hành chính.

Vui lòng tuân thủ các quy tắc sau:
1. Truy vấn được đặt trong thẻ <query>...</query>.
2. Danh sách các trường cho phép lọc sẽ được cung cấp trong thẻ <indexes>...</indexes>.
3. Chỉ sử dụng các trường có trong <indexes>. Không tự tạo thêm trường mới.
4. Chỉ sinh filter nếu bạn chắc chắn rằng ý định của người dùng tương ứng với tên trường và giá trị hợp lệ.
5. Không nên suy đoán. Nếu không tìm được trường phù hợp, hãy trả về bộ lọc rỗng.
6. Nếu người dùng đề cập đến điều gì đó cần loại trừ, hãy đưa vào mục `must_not`.
7. Nếu truy vấn có chứa nhiều điều kiện, hãy kết hợp tất cả trong `must` (và `must_not` nếu có loại trừ).
8. Không cần sử dụng `should` và `min_should` trừ khi thực sự cần thiết.
9. Luôn ưu tiên độ chính xác hơn số lượng điều kiện lọc. Nếu không chắc chắn, hãy bỏ qua.
10. Giải thích các trường có trong <indexes> để đảm bảo hiểu đúng ý định của người dùng.
Giải thích các trường quan trọng:
    - **form_code** (`KEYWORD`): Mã số biểu mẫu/giấy tờ. VD: `"CT01"`, `"TK02"`.
    - **form_name** (`KEYWORD`): Tên đầy đủ của biểu mẫu. VD: `"tờ khai thay đổi thông tin cư trú"`.
    - **field_no** (`KEYWORD`): Số thứ tự của trường trong biểu mẫu. VD: `"1"`, `"2"`, `"3"`.
    - **field_name** (`KEYWORD`): Tên của trường thông tin. VD: `"họ, chữ đệm và tên"`, `"ngày, tháng, năm sinh"`.
    - **chunk_type** (`KEYWORD`): Loại nội dung. VD: `"hướng_dẫn_điền"`, `"yêu_cầu"`, `"ghi_chú"`.
    - **category** (`KEYWORD`): Danh mục tài liệu. VD: `"form"`, `"document"`.
"""


FILTER_PROMPT_TERM = """
Bạn là một trợ lý AI có nhiệm vụ trích xuất bộ lọc (filter) từ truy vấn tiếng Việt để phục vụ tìm kiếm thuật ngữ và định nghĩa pháp lý, hành chính.
Vui lòng tuân thủ các quy tắc sau:
1. Truy vấn được đặt trong thẻ <query>...</query>.
2. Danh sách các trường cho phép lọc sẽ được cung cấp trong thẻ <indexes>...</indexes>.
3. Chỉ sử dụng các trường có trong <indexes>. Không tự tạo thêm trường mới.
4. Chỉ sinh filter nếu bạn chắc chắn rằng ý định của người dùng tương ứng với tên trường và giá trị hợp lệ.
5. Không nên suy đoán. Nếu không tìm được trường phù hợp, hãy trả về bộ lọc rỗng.
6. Nếu người dùng đề cập đến điều gì đó cần loại trừ, hãy đưa vào mục `must_not`.
7. Nếu truy vấn có chứa nhiều điều kiện, hãy kết hợp tất cả trong `must` (và `must_not` nếu có loại trừ).
8. Không cần sử dụng `should` và `min_should` trừ khi thực sự cần thiết.
9. Tất cả giá trị được sinh ra phải là chữ thường (lowercase).
10. Luôn ưu tiên độ chính xác hơn số lượng điều kiện lọc. Nếu không chắc chắn, hãy bỏ qua.

Giải thích các trường quan trọng:
    - **term** (`KEYWORD`): Thuật ngữ cần tra cứu. VD: `"nơi thường trú"`, `"nơi tạm trú"`, `"cư trú hợp pháp"`.
    - **content** (`TEXT`): Nội dung định nghĩa của thuật ngữ (có thể tìm kiếm full-text). VD: tìm kiếm các thuật ngữ có chứa từ "đăng ký" hoặc "sinh sống".
    - **category** (`KEYWORD`): Danh mục thuật ngữ. VD: `"term"`, `"definition"`, `"legal_term"`.

Lưu ý đặc biệt:
- Khi người dùng tìm kiếm thuật ngữ, ưu tiên sử dụng trường `term` với từ khóa chính xác.
- Khi người dùng tìm kiếm theo nội dung/định nghĩa, sử dụng trường `content` với tìm kiếm full-text.
- Hỗ trợ tìm kiếm các thuật ngữ liên quan đến: cư trú, đăng ký, hành chính, pháp lý.
- Có thể kết hợp tìm kiếm cả thuật ngữ và nội dung định nghĩa.
"""

FILTER_PROMPT_TEMPLATE = """
Bạn là một trợ lý AI có nhiệm vụ trích xuất bộ lọc từ truy vấn tiếng Việt để phục vụ tìm kiếm mẫu văn bản và template.

Vui lòng tuân thủ các quy tắc sau:
1. Truy vấn được đặt trong thẻ <query>...</query>.
2. Danh sách các trường cho phép lọc sẽ được cung cấp trong thẻ <indexes>...</indexes>.
3. Chỉ sử dụng các trường có trong <indexes>. Không tự tạo thêm trường mới.
4. Chỉ sinh filter nếu bạn chắc chắn rằng ý định của người dùng tương ứng với tên trường và giá trị hợp lệ.
5. Không nên suy đoán. Nếu không tìm được trường phù hợp, hãy trả về bộ lọc rỗng.
6. Nếu người dùng đề cập đến điều gì đó cần loại trừ, hãy đưa vào mục `must_not`.
7. Nếu truy vấn có chứa nhiều điều kiện, hãy kết hợp tất cả trong `must` (và `must_not` nếu có loại trừ).
8. Không cần sử dụng `should` và `min_should` trừ khi thực sự cần thiết.
9. Luôn ưu tiên độ chính xác hơn số lượng điều kiện lọc. Nếu không chắc chắn, hãy bỏ qua.
10. Giải thích các trường có trong <indexes> để đảm bảo hiểu đúng ý định của người dùng.
Giải thích các trường quan trọng:
    - **code** (`KEYWORD`): Mã số mẫu văn bản. VD: `"CT01"`, `"TK02"`.
    - **name** (`KEYWORD`): Tên đầy đủ của mẫu văn bản. VD: `"tờ khai thay đổi thông tin cư trú"`.
    - **description** (`TEXT`): Mô tả chi tiết về mẫu văn bản.
    - **procedures** (`TEXT`): Các thủ tục liên quan đến mẫu văn bản.
    - **category** (`KEYWORD`): Danh mục tài liệu. VD: `"templates"`.
"""
# FORMATTED_INDEXES_
FORMATTED_INDEXES_PROCEDURE = '- competent_authority - KEYWORD\n- decision_number - KEYWORD\n- implementing_agency - KEYWORD\n- application_receiving_address - KEYWORD\n- coordinating_agency - KEYWORD\n- implementation_subject - KEYWORD\n- implementation_result - KEYWORD\n- procedure_name - KEYWORD\n- category - KEYWORD\n- source_section - KEYWORD\n- procedure_code - KEYWORD\n- procedure_type - KEYWORD\n- field - KEYWORD\n- content_type - KEYWORD\n- table_title - KEYWORD\n- authorized_agency - KEYWORD\n- implementation_level - KEYWORD'
FORMATTED_INDEXES_LEGAL= '- type - KEYWORD\n- point - KEYWORD\n- section - KEYWORD\n- law_name - KEYWORD\n- law_type - KEYWORD\n- promulgator - KEYWORD\n- category - KEYWORD\n- promulgation_date - KEYWORD\n- clause - KEYWORD\n- chapter - KEYWORD\n- law_ref - KEYWORD\n- article - KEYWORD\n- parent_id - KEYWORD\n- effective_date - KEYWORD\n- id - KEYWORD\n- law_code - KEYWORD\n- parent_type - KEYWORD'
FORMATTED_INDEXES_FROM = '- form_code - KEYWORD\n- field_name - KEYWORD\n- chunk_type - KEYWORD\n- form_name - KEYWORD\n- category - KEYWORD\n- field_no - KEYWORD'
FORMATTED_INDEXES_TERM = '- content - TEXT\n- category - KEYWORD\n- term - KEYWORD'
FORMATTED_INDEXES_TEMPLATE = '- code - KEYWORD\n- name - KEYWORD\n- description - TEXT\n- procedures - TEXT\n- category - KEYWORD'


def automate_filtering(user_query, formatted_indexes, filter_prompt):
    try:
        # Use the raw Gemini client instead of instructor
        prompt = f"{filter_prompt.strip()}\n\n<query>{user_query}</query>\n<indexes>\n{formatted_indexes}\n</indexes>"
        response = gemini_model.generate_content(prompt)
        
        # For now, return empty filter to avoid the async issue
        # TODO: Implement proper JSON parsing from response
        return Filter()
    except Exception as e:
        print(f"Error in automate_filtering: {e}")
        # Return empty filter on error
        return Filter()



def search_qdrant(collection_name, query_embedding, query, limit=5):
    # return qdrant_client.search(
    #     collection_name=collection_name,
    #     query_vector=query_embedding,
    #     limit=limit
    # ) 
    # if ["legal_chunks", "form_chunks", "term_chunks", "procedure_chunks"]
    print("###" + collection_name + "###")
    print("###" + collection_name + "###")
    print("###" + collection_name + "###")
    print("###" + query + "###")
    print("###" + query + "###")
    print("###" + collection_name + "###")
    print("###" + collection_name + "###")
    print("###" + collection_name + "###")
    print("###" + collection_name + "###")
    print("###" + collection_name + "###")


    if collection_name == "procedure_chunks":
        filter_prompt = FILTER_PROMPT_PROCEDURE
        formatted_indexes = FORMATTED_INDEXES_PROCEDURE
    elif collection_name == "legal_chunks":
        filter_prompt = FILTER_PROMPT_LEGAL
        formatted_indexes = FORMATTED_INDEXES_LEGAL
    elif collection_name == "form_chunks":
        filter_prompt = FILTER_PROMPT_FROM
        formatted_indexes = FORMATTED_INDEXES_FROM
    elif collection_name == "term_chunks":
        filter_prompt = FILTER_PROMPT_TERM
        formatted_indexes = FORMATTED_INDEXES_TERM
    elif collection_name == "template_chunks":
        filter_prompt = FILTER_PROMPT_TEMPLATE
        formatted_indexes = FORMATTED_INDEXES_TEMPLATE
    else :
        return qdrant_client.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=limit
        ) 

    filter_condition = automate_filtering(user_query = query, formatted_indexes= formatted_indexes, filter_prompt= filter_prompt)
    
    return qdrant_client.query_points(
        collection_name=collection_name,
        query=query_embedding,
        query_filter = filter_condition,
        limit= limit,
        with_payload=True, # Trả về payload
        with_vectors=False # Không trả về vector
    ).points , filter_condition
