import boto3
from typing import Dict, Optional
import time



class Guardrails:
    """
    GuardrailService kiểm tra và bảo vệ nội dung truy vấn liên quan đến
    thủ tục hành chính, luật, giấy tờ và thuật ngữ trong hệ thống.
    """

    def __init__(
        self,
        region_name: str = "us-east-1",
        guardrail_id: Optional[str] = None,
        guardrail_version: str = "DRAFT"
    ):
        self.bedrock_runtime = boto3.client("bedrock-runtime", region_name=region_name)
        self.guardrail_id = guardrail_id
        self.guardrail_version = guardrail_version

    def apply_guardrail(
        self,
        text: str,
        source_type: str = "INPUT"
    ) -> dict:
        """
        Dùng ApplyGuardrail API để kiểm tra nội dung riêng biệt với mô hình.
        """
        try:
            response = self.bedrock_runtime.apply_guardrail(
                guardrailIdentifier=self.guardrail_id,
                guardrailVersion=self.guardrail_version,
                source=source_type,
                content=[{"text": {"text": text}}]
            )

            action = response.get("action", "N/A")
            outputs = response.get("outputs", [])
            assessments = response.get("assessments", [])

            return {
                "action": action,
                "outputs": outputs,
                "assessments": assessments
            }

        except Exception as e:
            # return {"error": str(e)}
            from pprint import pprint
            pprint("ERROR class Guardrails")
            pprint("ERROR class Guardrails")
            pprint("ERROR class Guardrails")
            pprint("ERROR class Guardrails")
            pprint("ERROR class Guardrails")

            return {
                "action": "NONE",
                "outputs": str(e),
                "assessments": str(e),
                "error": str(e)
            }
        
    

    def validate_input(self, user_query: str, messages: Optional[list] = None) -> Dict:
        guardrail_result = self.apply_guardrail(
            text=user_query,
            source_type='INPUT'
        )
        result = {}

        action = guardrail_result.get("action", "NONE")
        if action == "GUARDRAIL_INTERVENED":
            result['is_safe'] = False
            result['block_reason'] = "'Xin lỗi, tôi không thể hỗ trợ yêu cầu này vì nó không tuân thủ chính sách sử dụng an toàn và có trách nhiệm. Nếu bạn có câu hỏi khác, tôi rất sẵn lòng giúp đỡ!"
        else:
            result['is_safe'] = True
        
        return result


    def validate_output(self, text: str) -> Dict:
        start_time = time.time()
        guardrail_result = self.apply_guardrail(
            text=text,
            source_type='OUTPUT'
        )
        result = {}

        action = guardrail_result.get("action", "NONE")
        if action == "GUARDRAIL_INTERVENED":
            result['is_safe'] = False
            result['block_reason'] = "'Xin lỗi, tôi không thể hỗ trợ yêu cầu này vì nó không tuân thủ chính sách sử dụng an toàn và có trách nhiệm. Nếu bạn có câu hỏi khác, tôi rất sẵn lòng giúp đỡ!"
        else:
            result['is_safe'] = True
        
        result["processing_time"] = time.time() - start_time
        return result

    def get_fallback_message(self, block_reason: str) -> str:
        """Trả về tin nhắn fallback nếu nội dung bị chặn."""
        return "Xin lỗi, tôi không thể hỗ trợ câu hỏi này. Vui lòng hỏi về lĩnh vực pháp luật Việt Nam."