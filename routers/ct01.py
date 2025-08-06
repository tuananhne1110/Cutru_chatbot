from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import requests
import io
from docx import Document
import tempfile
import os

router = APIRouter(prefix="/api/ct01", tags=["CT01"])

class CT01FormData(BaseModel):
    formData: Dict[str, Any]
    cccdData: Optional[Dict[str, Any]] = None
    template: Optional[Dict[str, Any]] = None
    type: str = "docx"

class CT01SubmitData(BaseModel):
    formData: Dict[str, Any]
    cccdData: Optional[Dict[str, Any]] = None

@router.post("/generate")
async def generate_ct01_file(data: CT01FormData):
    """
    Tạo file CT01 từ template HTML với data đã điền
    """
    try:
        print(f"🔍 Received data: {data.formData}")
        print(f"🔍 Template info: {data.template}")
        
        # Đọc file ct01.html template
        template_path = "ct01.html"
        print(f"🔍 Reading HTML template from: {template_path}")
        
        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        print(f"HTML template loaded successfully: {len(html_content)} characters")
        
        # Điền data vào HTML template với cccd_data
        filled_html = fill_html_template_with_data(html_content, data.formData, data.cccdData)
        print(f"Data filled into HTML template")
        
        if data.type == "html":
            # Trả về HTML
            from fastapi.responses import Response
            filename = f"CT01-{data.template.get('code', 'CT01')}.html"
            return Response(
                content=filled_html,
                media_type="text/html",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        else:
            # Convert HTML to PDF hoặc DOCX
            output_file = convert_html_to_format(filled_html, data.type)
            
            # Trả về file
            from fastapi.responses import StreamingResponse
            
            filename = f"CT01-{data.template.get('code', 'CT01')}.{data.type}"
            media_type = "application/pdf" if data.type == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            
            print(f"Returning file: {filename}")
            
            return StreamingResponse(
                io.BytesIO(output_file),
                media_type=media_type,
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating file: {str(e)}")

@router.post("/submit")
async def submit_ct01_form(data: CT01SubmitData):
    """
    Nộp form CT01 trực tuyến
    """
    try:
        # TODO: Implement online submission logic
        # Có thể lưu vào database, gửi email, etc.
        
        return {
            "success": True,
            "message": "Form submitted successfully",
            "reference_id": f"CT01-{len(data.formData)}-{hash(str(data.formData)) % 10000}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting form: {str(e)}")

def fill_html_template_with_data(html_content: str, form_data: Dict[str, Any], cccd_data: Dict[str, Any] = None) -> str:
    """
    Điền data vào template HTML
    """
    print(f"🔍 Filling HTML template with data: {form_data}")
    if cccd_data:
        print(f"🔍 CCCD data available: {cccd_data}")
    
    # Parse HTML với BeautifulSoup
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    replacements_made = 0
    
    # Helper function to get data with fallback to CCCD
    def get_field_value(field_name: str, cccd_field: str = None) -> str:
        # Ưu tiên form_data, fallback sang cccd_data nếu có
        value = form_data.get(field_name, "")
        if not value and cccd_data and cccd_field:
            value = cccd_data.get(cccd_field, "")
        return str(value) if value else ""
    
    # 1. Điền "Kính gửi" - tìm và thay thế chuỗi có dấu ...
    kinh_gui_element = soup.find(string=lambda text: text and "Kính gửi" in text and "..." in text)
    if kinh_gui_element and form_data.get("co_quan_tiep_nhan"):
        new_text = kinh_gui_element.replace("......................................................................................", form_data["co_quan_tiep_nhan"])
        kinh_gui_element.replace_with(new_text)
        replacements_made += 1
        print(f"Filled 'Kính gửi': {form_data['co_quan_tiep_nhan']}")
    
    # 2. Điền "Họ, chữ đệm và tên" - với fallback từ CCCD
    ho_ten_element = soup.find(string=lambda text: text and "1. Họ, chữ đệm và tên:" in text)
    ho_ten = get_field_value("ho_ten", "personName")
    if ho_ten_element and ho_ten:
        new_text = ho_ten_element + " " + ho_ten
        ho_ten_element.replace_with(new_text)
        replacements_made += 1
        print(f"Filled 'Họ tên': {ho_ten}")
    
    # 3. Điền ngày sinh - với fallback từ CCCD
    ngay_sinh_element = soup.find(string=lambda text: text and "2. Ngày, tháng, năm sinh:" in text and "............/............./....................... 3. Giới tính:" in text)
    ngay_sinh = get_field_value("ngay_sinh", "dateOfBirth")
    gioi_tinh = get_field_value("gioi_tinh", "gender")
    
    if ngay_sinh_element and ngay_sinh:
        # Parse ngày sinh - handle both formats
        if "-" in ngay_sinh:  # yyyy-mm-dd (từ form)
            parts = ngay_sinh.split("-")
            day, month, year = parts[2], parts[1], parts[0]
        elif "/" in ngay_sinh:  # dd/mm/yyyy (từ CCCD)
            parts = ngay_sinh.split("/")
            day, month, year = parts[0], parts[1], parts[2] if len(parts) == 3 else ""
        else:
            day, month, year = "", "", ""
        
        new_text = f"2. Ngày, tháng, năm sinh: {day}/{month}/{year} 3. Giới tính: {gioi_tinh}"
        ngay_sinh_element.replace_with(new_text)
        replacements_made += 1
        print(f"Filled 'Ngày sinh': {day}/{month}/{year}, Giới tính: {gioi_tinh}")
    
    # 4. Điền số định danh cá nhân vào các ô - với fallback từ CCCD
    id_boxes = soup.find_all("div", class_="id-box")
    so_dinh_danh = get_field_value("so_dinh_danh", "idCode") or get_field_value("so_cccd", "idCode")
    if so_dinh_danh and len(id_boxes) >= 12:
        so_dinh_danh = str(so_dinh_danh).replace(" ", "").replace("-", "")
        for i, digit in enumerate(so_dinh_danh[:12]):
            if i < len(id_boxes):
                id_boxes[i].string = digit
                replacements_made += 1
        print(f"Filled 'Số định danh': {so_dinh_danh}")
    
    # 5. Điền số điện thoại - tìm với dấu chấm chính xác
    sdt_element = soup.find(string=lambda text: text and "5. Số điện thoại liên hệ: ..............." in text)
    sdt = get_field_value("dien_thoai") or get_field_value("so_dien_thoai")
    if sdt_element and sdt:
        new_text = sdt_element.replace("...............", sdt)
        sdt_element.replace_with(new_text)
        replacements_made += 1
        print(f"Filled 'SĐT': {sdt}")
    
    # 6. Điền email - tìm exact text
    email_element = soup.find(string="6. Email:")
    email = get_field_value("email")
    if email_element and email:
        new_text = f"6. Email: {email}"
        email_element.replace_with(new_text)
        replacements_made += 1
        print(f"Filled 'Email': {email}")
    
    # 6. Điền thông tin chủ hộ - với fallback
    chu_ho_element = soup.find(string=lambda text: text and "7. Họ, chữ đệm và tên chủ hộ:" in text and "8. Mối quan hệ với chủ hộ:" in text)
    if chu_ho_element:
        chu_ho = get_field_value("chu_ho") or get_field_value("ho_ten", "personName")  # Fallback to person name
        quan_he = get_field_value("quan_he_chu_ho", "") or "Chủ hộ"  # Default to "Chủ hộ"
        new_text = f"7. Họ, chữ đệm và tên chủ hộ: {chu_ho} 8. Mối quan hệ với chủ hộ: {quan_he}"
        chu_ho_element.replace_with(new_text)
        replacements_made += 1
        print(f"Filled 'Chủ hộ': {chu_ho}, Quan hệ: {quan_he}")
    
    # 7. Điền số định danh chủ hộ vào các ô thứ 2
    if form_data.get("dinh_danh_chu_ho") and len(id_boxes) >= 24:
        dinh_danh_chu_ho = str(form_data["dinh_danh_chu_ho"]).replace(" ", "").replace("-", "")
        for i, digit in enumerate(dinh_danh_chu_ho[:12]):
            if i + 12 < len(id_boxes):
                id_boxes[i + 12].string = digit
                replacements_made += 1
        print(f"Filled 'Số định danh chủ hộ': {dinh_danh_chu_ho}")
    
    # 8. Điền nội dung đề nghị
    noi_dung_element = soup.find(string=lambda text: text and "10. Nội dung đề nghị" in text)
    if noi_dung_element and form_data.get("noi_dung_de_nghi"):
        parent = noi_dung_element.parent
        if parent:
            # Tạo paragraph mới cho nội dung đề nghị
            new_p = soup.new_tag("div", style="margin: 10px 0; padding-left: 20px;")
            new_p.string = form_data["noi_dung_de_nghi"]
            parent.insert_after(new_p)
            replacements_made += 1
            print(f"Filled 'Nội dung đề nghị': {form_data['noi_dung_de_nghi']}")
    
    # 9. Điền thông tin thành viên gia đình vào bảng
    if form_data.get("thanh_vien_gia_dinh"):
        table_rows = soup.select("table tbody tr")
        thanh_vien = form_data["thanh_vien_gia_dinh"]
        
        if isinstance(thanh_vien, list):
            for i, member in enumerate(thanh_vien[:len(table_rows)]):
                if i < len(table_rows):
                    cells = table_rows[i].find_all("td")
                    if len(cells) >= 6:
                        # STT
                        cells[0].string = str(i + 1)
                        # Họ tên
                        cells[1].string = member.get("ho_ten", "")
                        # Ngày sinh
                        cells[2].string = member.get("ngay_sinh", "")
                        # Giới tính
                        cells[3].string = member.get("gioi_tinh", "")
                        # Số định danh
                        cells[4].string = member.get("so_dinh_danh", "")
                        # Quan hệ với chủ hộ
                        cells[5].string = member.get("quan_he", "")
                        replacements_made += 6
            print(f"Filled {len(thanh_vien)} thành viên gia đình")
    
    # 10. Điền thông tin chữ ký (nếu có)
    signature_sections = soup.find_all("div", class_="signature-box")
    
    # Ý kiến chủ hộ
    if len(signature_sections) > 0 and form_data.get("chu_ho_ho_ten"):
        ho_ten_input = signature_sections[0].find(string=lambda text: text and "Họ và tên:" in text)
        if ho_ten_input:
            new_text = ho_ten_input.replace("........................", form_data["chu_ho_ho_ten"])
            ho_ten_input.replace_with(new_text)
            replacements_made += 1
        
        if form_data.get("chu_ho_dinh_danh"):
            dinh_danh_input = signature_sections[0].find(string=lambda text: text and "Số định danh cá nhân:" in text)
            if dinh_danh_input:
                new_text = dinh_danh_input.replace("........................", form_data["chu_ho_dinh_danh"])
                dinh_danh_input.replace_with(new_text)
                replacements_made += 1
    
    # Ý kiến chủ sở hữu chỗ ở
    if len(signature_sections) > 1 and form_data.get("chu_so_huu_ho_ten"):
        ho_ten_input = signature_sections[1].find(string=lambda text: text and "Họ và tên:" in text)
        if ho_ten_input:
            new_text = ho_ten_input.replace("........................", form_data["chu_so_huu_ho_ten"])
            ho_ten_input.replace_with(new_text)
            replacements_made += 1
        
        if form_data.get("chu_so_huu_dinh_danh"):
            dinh_danh_input = signature_sections[1].find(string=lambda text: text and "Số định danh cá nhân:" in text)
            if dinh_danh_input:
                new_text = dinh_danh_input.replace("........................", form_data["chu_so_huu_dinh_danh"])
                dinh_danh_input.replace_with(new_text)
                replacements_made += 1
    
    # Ý kiến cha, mẹ hoặc người giám hộ
    if len(signature_sections) > 2 and form_data.get("giam_ho_ho_ten"):
        ho_ten_input = signature_sections[2].find(string=lambda text: text and "Họ và tên:" in text)
        if ho_ten_input:
            new_text = ho_ten_input.replace("........................", form_data["giam_ho_ho_ten"])
            ho_ten_input.replace_with(new_text)
            replacements_made += 1
        
        if form_data.get("giam_ho_dinh_danh"):
            dinh_danh_input = signature_sections[2].find(string=lambda text: text and "Số định danh cá nhân:" in text)
            if dinh_danh_input:
                new_text = dinh_danh_input.replace("........................", form_data["giam_ho_dinh_danh"])
                dinh_danh_input.replace_with(new_text)
                replacements_made += 1
    
    print(f"Total replacements made: {replacements_made}")
    
    return str(soup)

def convert_html_to_format(html_content: str, format_type: str) -> bytes:
    """
    Convert HTML to PDF or DOCX
    """
    if format_type == "pdf":
        # Convert HTML to PDF using pdfkit or weasyprint
        try:
            import pdfkit
            pdf_bytes = pdfkit.from_string(html_content, False)
            return pdf_bytes
        except ImportError:
            print("pdfkit not available, using simple text export")
            return html_content.encode('utf-8')
    
    elif format_type == "docx":
        # Convert HTML to DOCX (simplified)
        try:
            from docx import Document
            from docx.shared import Inches
            
            doc = Document()
            # Add HTML content as text (simplified conversion)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            text_content = soup.get_text()
            
            doc.add_paragraph(text_content)
            
            output = io.BytesIO()
            doc.save(output)
            output.seek(0)
            return output.getvalue()
        except Exception as e:
            print(f"⚠️ DOCX conversion failed: {e}")
            return html_content.encode('utf-8')
    
    else:
        return html_content.encode('utf-8')