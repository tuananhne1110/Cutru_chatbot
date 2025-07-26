import sys
import os
from config.app_config import qdrant_client
from instructor import from_bedrock, Mode
from pydantic import BaseModel
from qdrant_client.models import Filter, Condition
import boto3


# | Field                                           | Index     |
# | ----------------------------------------------- | --------- |
# | `procedure_name`                                | `text`    |
# | `source_section`                                | `text`    |
# | `description`                                   | `text`    |
# | `note`, `requirements`, `implementation_result` | `text`    |
# | `procedure_code`                                | `keyword` |
# | `category`, `field`, `implementation_level`     | `keyword` |
# | `implementation_subject`                        | `keyword` |


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _setup_llm_client():
        bedrock_runtime = boto3.client("bedrock-runtime", region_name="us-east-1")
        return from_bedrock(
            client=bedrock_runtime,
            model="us.meta.llama4-scout-17b-instruct-v1:0",
            mode=Mode.BEDROCK_JSON,
        )

llm_client = _setup_llm_client()

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
    - **procedure_code** (`KEYWORD`): Mã số thủ tục hành chính. VD: "1.002755". Cần so khớp chính xác tuyệt đối.
    - **category** (`KEYWORD`): Nhóm nội dung. Thường là "Thủ tục hành chính". Danh sách giá trị cố định.
    - **content_type** (`KEYWORD`): Loại nội dung: "text" hoặc "table_row". Dùng để xác định dạng dữ liệu.
    - **implementing_agency** (`TEXT`): Cơ quan trực tiếp xử lý. VD: "Công an xã", "Phòng Tư pháp" — người dùng có thể nhập tự nhiên.
    - **implementation_subject** (`TEXT`): Đối tượng thực hiện. VD: "Công dân Việt Nam", "Tổ chức", "Người nước ngoài".
    - **coordinating_agency** (`TEXT`): Cơ quan phối hợp thực hiện (nếu có). Tên có thể dài, nhập tự nhiên.
    - **implementation_result** (`TEXT`): Kết quả xử lý. VD: "Cập nhật dữ liệu cư trú", "Cấp sổ tạm trú".
    - **implementation_level** (`KEYWORD`): Cấp hành chính thực hiện. VD: "Cấp Xã", "Cấp Huyện", "Cấp Tỉnh".
    - **procedure_name** (`TEXT`): Tên thủ tục hành chính. VD: "Gia hạn tạm trú", "Đăng ký tạm trú" — thường được nhập tự nhiên.
    - **competent_authority** (`TEXT`): Cơ quan có thẩm quyền quyết định. Có thể là nhiều loại tên dài, không cố định.
    - **field** (`KEYWORD`): Lĩnh vực quản lý. VD: "Cư trú", "Xuất nhập cảnh", "Hộ tịch". Danh mục ngắn và cố định.
    - **application_receiving_address** (`TEXT`): Địa điểm tiếp nhận hồ sơ. Thường là địa chỉ hoặc tên cơ quan.
    - **procedure_type** (`KEYWORD`): Loại thủ tục. VD: "TTHC được luật giao quy định chi tiết", "TTHC đặc thù".
    - **source_section** (`TEXT`): Phần nội dung gốc chỉ thuộc 1 trong 3 TỪ KHÓA SAU `"cách thức thực hiện"`, `"thành phần hồ sơ"`. `"căn cứ pháp lý"`
    - **decision_number** (`KEYWORD`): Số hiệu quyết định ban hành thủ tục. VD: "1234/QĐ-BCA".
    - **authorized_agency** (`TEXT`): Cơ quan được ủy quyền thực hiện (nếu có). Tên có thể đa dạng, không chuẩn hoá hoàn toàn.
    - **table_title** (`TEXT`): Tiêu đề của bảng dữ liệu (nếu có). VD: "Cách thức thực hiện", "Thời hạn giải quyết".
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
    - **law_name** (`TEXT`): Tên đầy đủ của văn bản pháp luật. VD: "luật xuất nhập cảnh", "thông tư số 04/2016/TT-BNG".
    - **law_code** (`KEYWORD`): Mã số văn bản. VD: "04/2016/TT-BNG".
    - **promulgation_date** (`KEYWORD`): Ngày ban hành. VD: "30 tháng 6 năm 2016".
    - **effective_date** (`KEYWORD`): Ngày có hiệu lực. VD: "01 tháng 8 năm 2016".
    - **promulgator** (`TEXT`): Cơ quan ban hành. VD: "Bộ Ngoại giao", "Chính phủ".
    - **law_type** (`KEYWORD`): Loại văn bản. VD: "thông tư", "nghị định", "luật".
    - **chapter** (`KEYWORD`): Chương của văn bản. VD: "chương i", "chương ii".
    - **article** (`KEYWORD`): Điều cụ thể. VD: "điều 1", "điều 10".
    - **clause** (`KEYWORD`): Khoản trong điều. VD: "khoản 1", "khoản 2".
    - **point** (`KEYWORD`): Điểm trong khoản. VD: "điểm a", "điểm b".
    - **category** (`KEYWORD`): Danh mục phân loại. Mặc định là "law".
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
- **form_code** (`KEYWORD`): Mã số biểu mẫu/giấy tờ. VD: "CT01", "CT02".
- **form_name** (`TEXT`): Tên đầy đủ của biểu mẫu. VD: "tờ khai thay đổi thông tin cư trú".
- **field_no** (`KEYWORD`): Số thứ tự của trường trong biểu mẫu. VD: "1", "2", "3".
- **field_name** (`TEXT`): Tên của trường thông tin. VD: "họ, chữ đệm và tên", "ngày, tháng, năm sinh".
- **chunk_type** (`KEYWORD`): Loại nội dung. VD: "hướng_dẫn_điền", "yêu_cầu", "ghi_chú".
- **category** (`KEYWORD`): Danh mục tài liệu. VD: "form", "document".
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
    - **term** (`TEXT`): Thuật ngữ cần tra cứu. VD: `"nơi thường trú"`, `"nơi tạm trú"`, `"cư trú hợp pháp"`.
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
    - **code** (`KEYWORD`): Mã số mẫu văn bản. VD: `"CT01"`, `"CT02"`.
    - **name** (`KEYWORD`): Tên đầy đủ của mẫu văn bản. VD: `"tờ khai thay đổi thông tin cư trú"`.
    - **description** (`TEXT`): Mô tả chi tiết về mẫu văn bản.
    - **procedures** (`TEXT`): Các thủ tục liên quan đến mẫu văn bản.
    - **category** (`KEYWORD`): Danh mục tài liệu. VD: `"templates"`.
"""
# FORMATTED_INDEXES_
FORMATTED_INDEXES_PROCEDURE = '''\
- competent_authority - TEXT
- decision_number - KEYWORD
- implementing_agency - TEXT
- application_receiving_address - TEXT
- coordinating_agency - TEXT
- implementation_subject - TEXT
- implementation_result - TEXT
- procedure_name - TEXT
- category - KEYWORD
- source_section - TEXT
- procedure_code - KEYWORD
- procedure_type - KEYWORD
- field - KEYWORD
- content_type - KEYWORD
- table_title - TEXT
- authorized_agency - TEXT
- implementation_level - KEYWORD'''



FORMATTED_INDEXES_LEGAL = '''\
- type - KEYWORD
- point - KEYWORD
- section - KEYWORD
- law_name - TEXT
- law_type - KEYWORD
- promulgator - TEXT
- category - KEYWORD
- promulgation_date - KEYWORD
- clause - KEYWORD
- chapter - KEYWORD
- law_ref - KEYWORD
- article - KEYWORD
- parent_id - KEYWORD
- effective_date - KEYWORD
- id - KEYWORD
- law_code - KEYWORD
- parent_type - KEYWORD'''

FORMATTED_INDEXES_FORM = """
- form_code - KEYWORD
- form_name - TEXT
- field_no - KEYWORD
- field_name - TEXT
- chunk_type - KEYWORD
- category - KEYWORD
"""

FORMATTED_INDEXES_TERM = """
- category - KEYWORD
- term - TEXT
"""
FORMATTED_INDEXES_TEMPLATE = """
- code - KEYWORD
- name - KEYWORD
- description - TEXT
- procedures - TEXT
- category - KEYWORD
"""


def automate_filtering(user_query, formatted_indexes, filter_prompt):
    response = llm_client.messages.create(
        response_model=QdrantFilterWrapper,
        messages=[
            {"role": "user", "content": filter_prompt.strip()},
            {"role": "assistant", "content": "Đã hiểu. Tôi sẽ tuân thủ các quy tắc."},
            {"role": "user", "content": f"<query>{user_query}</query>\n<indexes>\n{formatted_indexes}\n</indexes>"}
        ]
    )

    return response.to_qdrant_filter()



def search_qdrant(collection_name, query_embedding, query, limit=5):
    # if ["legal_chunks", "form_chunks", "term_chunks", "procedure_chunks"]
    print("###" + query + "###")
    print("###" + query + "###")
    print("###" + query + "###")
    print("###" + query + "###")
    print("###" + query + "###")



    if collection_name == "procedure_chunks":
        filter_prompt = FILTER_PROMPT_PROCEDURE
        formatted_indexes = FORMATTED_INDEXES_PROCEDURE
    elif collection_name == "legal_chunks":
        filter_prompt = FILTER_PROMPT_LEGAL
        formatted_indexes = FORMATTED_INDEXES_LEGAL
    elif collection_name == "form_chunks":
        filter_prompt = FILTER_PROMPT_FROM
        formatted_indexes = FORMATTED_INDEXES_FORM
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
    
    print("*###" + "_"*50 + "###*")
    print(filter_condition )
    print("###" + "_"*50 + "###")
    

    try:
        filter_result = qdrant_client.query_points(
            collection_name=collection_name,
            query=query_embedding,
            query_filter=filter_condition,
            limit=limit,
            with_payload=True,  # Trả về payload
            with_vectors=False  # Không trả về vector
        ).points

        if filter_condition is not None and len(filter_result) == 0:
            vector_search_results = qdrant_client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=limit,
                with_payload=True
            )
            return vector_search_results, filter_condition
        else:
            return filter_result, filter_condition

    except Exception as e:
        # Nếu query_points bị lỗi, fallback sang search
        vector_search_results = qdrant_client.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=limit,
            with_payload=True
        )
        return vector_search_results, filter_condition


def search_qdrant_by_parent_id(collection_name, parent_id, limit=30):
    """Truy vấn Qdrant lấy các chunk theo parent_id (không dùng embedding/query)"""
    filter_condition = {
        "must": [
            {"key": "parent_id", "match": {"value": parent_id}}
        ]
    }
    results, _ = qdrant_client.scroll(
        collection_name=collection_name,
        scroll_filter=filter_condition,
        limit=limit,
        with_payload=True,
        with_vectors=False
    )
    # results đã là list các điểm
    return results

def search_qdrant_by_id(collection_name, doc_id, limit=1):
    """
    Truy vấn Qdrant lấy các chunk theo id (thường dùng để lấy điều cha của khoản).
    """
    filter_condition = {
        "must": [
            {"key": "id", "match": {"value": doc_id}}
        ]
    }
    results, _ = qdrant_client.scroll(
        collection_name=collection_name,
        scroll_filter=filter_condition,
        limit=limit,
        with_payload=True,
        with_vectors=False
    )
    return results
