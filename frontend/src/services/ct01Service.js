import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.REACT_APP_SUPABASE_URL || process.env.SUPABASE_URL || 'https://rjrqtogyzmgyqvryxfyk.supabase.co';
const supabaseKey = process.env.REACT_APP_SUPABASE_ANON_KEY || process.env.SUPABASE_KEY || 'your_anon_key_here';

console.log('Supabase URL:', supabaseUrl);
console.log('Supabase Key available:', !!supabaseKey && supabaseKey !== 'your_anon_key_here');
console.log('Environment variables:');
console.log('- REACT_APP_SUPABASE_URL:', process.env.REACT_APP_SUPABASE_URL);
console.log('- REACT_APP_SUPABASE_ANON_KEY:', process.env.REACT_APP_SUPABASE_ANON_KEY);
console.log('- SUPABASE_URL:', process.env.SUPABASE_URL);
console.log('- SUPABASE_KEY length:', process.env.SUPABASE_KEY ? process.env.SUPABASE_KEY.length : 'undefined');
console.log('- SUPABASE_KEY starts with:', process.env.SUPABASE_KEY ? process.env.SUPABASE_KEY.substring(0, 20) + '...' : 'undefined');

// Chỉ tạo client nếu có URL và key hợp lệ
let supabase = null;
if (supabaseUrl && supabaseKey && supabaseKey !== 'your_anon_key_here') {
  try {
    supabase = createClient(supabaseUrl, supabaseKey);
    console.log('Supabase client created successfully');
  } catch (error) {
    console.warn('Supabase client creation failed:', error);
  }
} else {
  console.warn('Supabase credentials not available');
}

export const ct01Service = {
  // Lấy biểu mẫu CT01 từ file local
  async getCT01Template() {
    try {
      // Luôn load từ file local để đảm bảo consistency
      console.log('Loading CT01 template from local file...');
      
      // Fetch từ file local ct01-template.json
      const response = await fetch('/ct01-template.json');
      if (!response.ok) {
        throw new Error('Failed to load local template file');
      }
      
      const template = await response.json();
      console.log('Successfully loaded template from local file:', template);
      
      return this.normalizeTemplate(template);
    } catch (error) {
      console.error('Error loading CT01 template:', error);
      // Fallback to minimal template nếu không load được
      return {
        form_code: 'CT01',
        form_title: 'TỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ',
        code: 'CT01',
        name: 'Biểu mẫu CT01',
        description: 'Template loading failed',
        fields: []
      };
    }
  },

  // Normalize template format
  normalizeTemplate(template) {
    // Add backward compatibility fields
    return {
      ...template,
      code: template.form_code || template.code || 'CT01',
      name: template.form_title || template.name || 'Biểu mẫu CT01',
      description: template.description || `Biểu mẫu ${template.form_code || 'CT01'}`,
      file_url: template.file_url || 'https://rjrqtogyzmgyqvryxfyk.supabase.co/storage/v1/object/public/bieumau/ct01.docx',
      template_url: template.template_url || template.file_url || 'https://rjrqtogyzmgyqvryxfyk.supabase.co/storage/v1/object/public/bieumau/ct01.docx',
      // Normalize fields - ensure both id and name are available
      fields: (template.fields || []).map(field => ({
        ...field,
        name: field.id || field.name || field.label?.toLowerCase().replace(/\s+/g, '_'),
        id: field.id || field.name || field.label?.toLowerCase().replace(/\s+/g, '_')
      }))
    };
  },



  // Lưu dữ liệu CCCD
  async saveCCCDData(cccdData) {
    try {
      if (!supabase) {
        console.warn('Supabase not available, skipping CCCD data save');
        return { id: Date.now(), ...cccdData };
      }

      const { data, error } = await supabase
        .from('cccd_data')
        .insert({
          so_cccd: cccdData.so_cccd,
          ho_ten: cccdData.ho_ten,
          ngay_sinh: cccdData.ngay_sinh,
          gioi_tinh: cccdData.gioi_tinh,
          quoc_tich: cccdData.quoc_tich,
          dia_chi: cccdData.dia_chi,
          noi_sinh: cccdData.noi_sinh,
          ngay_cap: cccdData.ngay_cap,
          noi_cap: cccdData.noi_cap,
          ngay_het_han: cccdData.ngay_het_han,
          dac_diem_nhan_dang: cccdData.dac_diem_nhan_dang,
          created_at: new Date().toISOString()
        })
        .select()
        .single();

      if (error) throw error;
      return data;
    } catch (error) {
      console.error('Error saving CCCD data:', error);
      throw error;
    }
  },

  // Lưu dữ liệu form CT01
  async saveCT01Form(formData, cccdDataId) {
    try {
      const { data, error } = await supabase
        .from('ct01_forms')
        .insert({
          cccd_data_id: cccdDataId,
          ho_ten: formData.ho_ten,
          so_cccd: formData.so_cccd,
          ngay_sinh: formData.ngay_sinh,
          gioi_tinh: formData.gioi_tinh,
          dia_chi: formData.dia_chi,
          so_dien_thoai: formData.so_dien_thoai,
          email: formData.email,
          nghe_nghiep: formData.nghe_nghiep,
          thu_nhap: formData.thu_nhap,
          thue_da_khau_tru: formData.thue_da_khau_tru,
          so_nguoi_phu_thuoc: formData.so_nguoi_phu_thuoc,
          ghi_chu: formData.ghi_chu,
          status: 'completed',
          created_at: new Date().toISOString()
        })
        .select()
        .single();

      if (error) throw error;
      return data;
    } catch (error) {
      console.error('Error saving CT01 form:', error);
      throw error;
    }
  },

  // Lấy lịch sử form CT01
  async getCT01History() {
    try {
      const { data, error } = await supabase
        .from('ct01_forms')
        .select(`
          *,
          cccd_data:cccd_data_id (
            so_cccd,
            ho_ten,
            ngay_sinh
          )
        `)
        .order('created_at', { ascending: false });

      if (error) throw error;
      return data;
    } catch (error) {
      console.error('Error fetching CT01 history:', error);
      throw error;
    }
  },

  // Tạo file CT01
  async generateCT01File(formData, cccdData, template, type = 'html') {
    try {
      console.log('Generating CT01 file with data:', formData);
      console.log('Using template:', template);
      console.log('Output type:', type);
      
      const response = await fetch('http://localhost:8000/api/ct01/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          formData,
          cccdData,
          template: {
            code: template?.form_code || 'CT01',
            name: template?.form_title || 'TỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ'
          },
          type
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to generate file: ${errorText}`);
      }

      if (type === 'html') {
        // Trả về HTML content để hiển thị
        const htmlContent = await response.text();
        return new Blob([htmlContent], { type: 'text/html' });
      } else {
        // Trả về file binary (PDF, DOCX)
        return await response.blob();
      }
    } catch (error) {
      console.error('Error generating CT01 file:', error);
      // Fallback: simulate file generation
      return this.simulateFileGeneration(formData, template, type);
    }
  },

   // Simulate file generation (for development)
   simulateFileGeneration(formData, template, type = 'pdf') {
     console.log('Simulating file generation with data:', formData);
     console.log('Using template: ct01.docx from Supabase Storage');
     
     // Create a simple text file as simulation
     const content = `TỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ\n` +
                    `Mẫu số: CT01\n\n` +
                    `I. THÔNG TIN NGƯỜI KÊ KHAI\n` +
                    `1. Họ, chữ đệm và tên: ${formData.ho_ten || ''}\n` +
                    `2. Ngày, tháng, năm sinh: ${formData.ngay_sinh || ''}\n` +
                    `3. Giới tính: ${formData.gioi_tinh || ''}\n` +
                    `4. Số định danh cá nhân: ${formData.so_dinh_danh || ''}\n` +
                    `5. Số điện thoại liên hệ: ${formData.dien_thoai || ''}\n` +
                    `6. Email: ${formData.email || ''}\n\n` +
                    `II. THÔNG TIN CHỦ HỘ\n` +
                    `1. Họ, chữ đệm và tên chủ hộ: ${formData.chu_ho || ''}\n` +
                    `2. Mối quan hệ với chủ hộ: ${formData.quan_he_chu_ho || ''}\n` +
                    `3. Số định danh cá nhân của chủ hộ: ${formData.dinh_danh_chu_ho || ''}\n\n` +
                    `III. NỘI DUNG ĐỀ NGHỊ\n` +
                    `${formData.noi_dung_de_nghi || ''}\n\n` +
                    `IV. Ý KIẾN CỦA CHỦ HỘ\n` +
                    `${formData.ykien_chu_ho || ''}\n\n` +
                    `V. Ý KIẾN CỦA CHỦ SỞ HỮU CHỖ Ở HỢP PHÁP\n` +
                    `Họ và tên chủ sở hữu: ${formData.chu_so_huu_ho_ten || ''}\n` +
                    `Số định danh chủ sở hữu: ${formData.chu_so_huu_dinh_danh || ''}\n` +
                    `Ý kiến: ${formData.ykien_chu_so_huu || ''}\n\n` +
                    `VI. Ý KIẾN CỦA CHA, MẸ HOẶC NGƯỜI GIÁM HỘ\n` +
                    `Họ và tên cha/mẹ/người giám hộ: ${formData.cha_me_ho_ten || ''}\n` +
                    `Số định danh cha/mẹ/người giám hộ: ${formData.cha_me_dinh_danh || ''}\n` +
                    `Ý kiến: ${formData.ykien_cha_me || ''}\n\n` +
                    `VII. NGƯỜI KÊ KHAI\n` +
                    `Họ và tên người kê khai: ${formData.nguoi_ke_khai || ''}\n\n` +
                    `\nFile này được tạo từ template gốc: ct01.docx\n` +
                    `Loại file: ${type}\n` +
                    `Thời gian tạo: ${new Date().toLocaleString('vi-VN')}`;
     
     const mimeType = type === 'pdf' ? 'application/pdf' : 
                      type === 'docx' ? 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' :
                      'text/plain';
     
     return new Blob([content], { type: mimeType });
   },

  // Nộp form trực tuyến
  async submitCT01Online(formData, cccdData) {
    try {
      const response = await fetch('/api/ct01/submit', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          formData,
          cccdData
        })
      });

      if (!response.ok) {
        throw new Error('Failed to submit form');
      }

      return await response.json();
    } catch (error) {
      console.error('Error submitting CT01 form:', error);
      throw error;
    }
  }
}; 