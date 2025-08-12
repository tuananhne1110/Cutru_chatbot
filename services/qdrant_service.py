import os
import sys
from typing import Optional

import boto3
from instructor import Mode, from_bedrock
from pydantic import BaseModel
from qdrant_client.models import Condition, Filter

from config.app_config import qdrant_client


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
    min_should: Optional[int] = None

    def to_qdrant_filter(self) -> Filter:
        from qdrant_client.models import MinShould
        
        # Chỉ tạo MinShould nếu có should conditions
        min_should_obj = None
        if self.min_should is not None and self.should:
            min_should_obj = MinShould(conditions=self.should, min_count=self.min_should)
        
        return Filter(
            must=self.must if self.must else None,
            must_not=self.must_not if self.must_not else None,
            should=self.should if self.should else None,
            min_should=min_should_obj
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

FILTER_PROMPT_LEGAL = """
Bạn là trợ lý AI chuyên trích xuất BỘ LỌC tìm kiếm (filter) cho cơ sở tri thức pháp luật về cư trú (Qdrant).

NHIỆM VỤ
- Nhận truy vấn tiếng Việt trong <query>...</query>
- Trả về JSON filter dùng cho Qdrant theo format quy định.
- Không giải thích, KHÔNG thêm text ngoài JSON.

TRƯỜNG ĐƯỢC PHÉP DÙNG (payload keys)
- chapter_content (TEXT): Nội dung chương/mục liên quan
- content (TEXT): Nội dung điều/khoản/điểm
- law_name (TEXT): Tên văn bản (vd: "Luật Cư trú 2020", "Nghị định 62/2021/NĐ-CP")
- law_type (KEYWORD): "Luật" | "Nghị định" | "Thông tư"
- category (KEYWORD): Nhóm chủ đề (vd: "cư trú", "lưu trú", "tạm trú", "thường trú", "tạm vắng")

QUY TẮC RA QUYẾT ĐỊNH
1) MUST (ràng buộc bắt buộc) — đưa vào khi truy vấn có:
   - TÊN hoặc LOẠI văn bản nêu rõ (vd: "Luật Cư trú", "Nghị định 62/2021").
     -> map chính xác: { "key":"law_type","match":{"text":"Luật"}} và/hoặc { "key":"law_name","match":{"text":"Luật Cư trú"} }
   - Tham chiếu cấu trúc: "Chương X", "Điều 20", "Khoản 2", "Điểm a"
     -> match trong "content" hoặc "chapter_content" (vd: "Điều 20", "Khoản 2")
   - Chủ đề hẹp, cụm từ khóa cốt lõi (vd: "thông báo lưu trú", "đăng ký tạm trú", "xóa đăng ký thường trú").
     -> ít nhất 1 điều kiện MUST cho cụm cốt lõi.

2) SHOULD (tăng độ liên quan, không bắt buộc)
   - Từ đồng nghĩa/biến thể ngôn ngữ cho chủ đề:
     * "thông báo lưu trú" ~ "khai báo lưu trú" ~ "báo lưu trú"
     * "phương tiện/phương thức/hình thức/cách thức"
     * "thời hạn/thời điểm/thời gian/trong vòng"
     * "đăng ký tạm trú" ~ "tạm trú" ~ "đăng ký lưu trú"
     * "thường trú" ~ "nhập hộ khẩu" (nếu phù hợp ngữ cảnh)
   - Thực thể ngữ nghĩa phụ trợ nếu có (chủ thể, hồ sơ, thẩm quyền...).

   Đặt "min_should" = 1 (hoặc 2 nếu có ≥2 nhóm từ đồng nghĩa rõ ràng). Không vượt quá chiều dài mảng "should".

3) MUST_NOT (loại trừ)
   - Chỉ dùng khi người hỏi nêu rõ loại trừ (vd: "không áp dụng cho người nước ngoài" -> nếu có nhãn trong dữ liệu).

4) Không bịa tên văn bản, số hiệu. Nếu truy vấn không nêu, **không** thêm "law_name"/"law_type".
5) Nếu không có từ khóa pháp lý rõ ràng → trả về JSON rỗng `{}`.
6) Ưu tiên đặt cụm chính vào `chapter_content` hoặc `content`. Có thể lặp cụm vào cả hai dưới dạng SHOULD để tăng recall.
7) Chỉ xuất JSON hợp lệ, các trường: "must" | "should" | "must_not" | "min_should". Bỏ hẳn trường rỗng.

MẪU JSON HỢP LỆ
{
  "must": [ { "key":"content","match":{"text":"Điều 20"}} ],
  "should": [ { "key":"content","match":{"text":"Khoản 2"}} ],
  "min_should": 1
}


ĐẦU VÀO
<indexes>
chapter_content, content, law_name, law_type, category
</indexes>
<query>{{user_query}}</query>

ĐẦU RA
- Chỉ in ra JSON theo format đã nêu, không bao gồm giải thích.
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
- law_name - TEXT
- law_code - KEYWORD
- law_type - KEYWORD
- promulgator - TEXT
- promulgation_date - KEYWORD
- effective_date - KEYWORD
- chapter - KEYWORD
- chapter_content - TEXT
- content - TEXT
- category - KEYWORD
- id - KEYWORD'''

FORMATTED_INDEXES_FORM = """
- form_code - KEYWORD
- form_name - TEXT
- field_no - KEYWORD
- field_name - TEXT
- chunk_type - KEYWORD
- category - KEYWORD
"""


FORMATTED_INDEXES_TEMPLATE = """
- code - KEYWORD
- name - KEYWORD
- description - TEXT
- procedures - TEXT
- category - KEYWORD
"""


def automate_filtering(user_query, formatted_indexes, filter_prompt):
    try:
        response = llm_client.messages.create(
            response_model=QdrantFilterWrapper,
            messages=[
                {"role": "user", "content": filter_prompt.strip()},
                {"role": "assistant", "content": "Đã hiểu. Tôi sẽ tuân thủ các quy tắc."},
                {"role": "user", "content": f"<query>{user_query}</query>\n<indexes>\n{formatted_indexes}\n</indexes>"}
            ]
        )
        return response.to_qdrant_filter()
    except Exception as e:
        print(f"Error in automate_filtering: {e}")
        return None



def search_qdrant(collection_name, query_embedding, query, limit=5):
    print("###" + query + "###")

    # Comment out filtering logic - only use vector search
    # if collection_name == "procedure_chunks":
    #     filter_prompt = FILTER_PROMPT_PROCEDURE
    #     formatted_indexes = FORMATTED_INDEXES_PROCEDURE
    # elif collection_name == "legal_chunks":
    #     filter_prompt = FILTER_PROMPT_LEGAL
    #     formatted_indexes = FORMATTED_INDEXES_LEGAL
    # elif collection_name == "form_chunks":
    #     filter_prompt = FILTER_PROMPT_FROM
    #     formatted_indexes = FORMATTED_INDEXES_FORM
    # elif collection_name == "template_chunks":
    #     filter_prompt = FILTER_PROMPT_TEMPLATE
    #     formatted_indexes = FORMATTED_INDEXES_TEMPLATE
    # else:
    #     return qdrant_client.search(
    #         collection_name=collection_name,
    #         query_vector=query_embedding,
    #         limit=limit
    #     ) 

    # filter_condition = automate_filtering(user_query=query, formatted_indexes=formatted_indexes, filter_prompt=filter_prompt)
    
    # print("*###" + "_"*50 + "###*")
    # print(filter_condition)
    # print("###" + "_"*50 + "###")
    
    # # Nếu automate_filtering thất bại, fallback về vector search ngay
    # if filter_condition is None:
    #     print("automate_filtering failed, falling back to vector search")
    #     return qdrant_client.search(
    #         collection_name=collection_name,
    #         query_vector=query_embedding,
    #         limit=limit,
    #         with_payload=True
    #     ), None

    # try:
    #     filter_result = qdrant_client.query_points(
    #         collection_name=collection_name,
    #         query=query_embedding,
    #         query_filter=filter_condition,
    #         limit=limit,
    #         with_payload=True,
    #         with_vectors=False
    #     ).points

    #     # Nếu có filter nhưng không có kết quả, fallback về vector search 
    #     if filter_condition is not None and len(filter_result) == 0:
    #         print(f"Filter returned {len(filter_result)} results, falling back to vector search")
    #         vector_search_results = qdrant_client.search(
    #             collection_name=collection_name,
    #             query_vector=query_embedding,
    #             limit=limit,
    #             with_payload=True
    #         )
    #         if hasattr(vector_search_results, 'points'):
    #             return vector_search_results.points, filter_condition
    #         else:
    #             return vector_search_results, filter_condition
    #     else:
    #         return filter_result, filter_condition

    # except Exception as e:
    #     vector_search_results = qdrant_client.search(
    #         collection_name=collection_name,
    #         query_vector=query_embedding,
    #         limit=limit,
    #         with_payload=True
    #     )
    #     if hasattr(vector_search_results, 'points'):
    #         return vector_search_results.points, filter_condition
    #     else:
    #         return vector_search_results, filter_condition

    # Simplified: Only use vector search without filtering - similar to vector retriever
    try:
        vector_search_results = qdrant_client.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=limit,
            with_payload=True
        )
        if hasattr(vector_search_results, 'points'):
            return vector_search_results.points
        else:
            return vector_search_results
    except Exception as e:
        print(f"Error in vector search: {e}")
        return []


# Đã bỏ hàm search_qdrant_by_parent_id vì không còn parent_id trong cấu trúc dữ liệu mới

def search_qdrant_by_id(collection_name, doc_id, limit=1):
    """Truy vấn Qdrant lấy các chunk theo id."""
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
