from copy import deepcopy
import boto3

from .base import BaseGuardrailsConfig, GuardrailsConfig
from ..utils.logger_utils import get_logger

logger = get_logger(__name__)

class BedrockGuardrails(BaseGuardrailsConfig):


    def __init__(self, global_config = None):
        super().__init__(global_config)

        self._init_guarldrails_config()
        self.bedrock_runtime = boto3.client("bedrock-runtime", region_name=self.guardrail_config.region_name)
    
    def _init_guarldrails_config(self) -> None:
        config_dict = self.global_config.__dict__
        config_dict["guardrails_params"] = {
            "guardrailIdentifier": self.global_config.guardrails_id,
            "guardrailVersion": self.global_config.guardrails_version,
        }
        config_dict["region_name"] = self.global_config.guardrails_region_name
        self.guardrail_config = GuardrailsConfig.from_dict(config_dict=config_dict)
        # logger.info(f"[BedrockLLM] Config: {self.guardrail_config}")



    def apply_guardrail(self, text: str, source_type: str) -> dict:
        self.guardrail_config.guardrails_params["source"] = source_type
        self.guardrail_config.guardrails_params["content"] = [{"text": {"text": text}}]
   

        try:
            response = self.bedrock_runtime.apply_guardrail(**self.guardrail_config.guardrails_params)
            action = response.get("action", "N/A")
            outputs = response.get("outputs", [])
            assessments = response.get("assessments", [])

            return {
                "action": action,
                "outputs": outputs,
                "assessments": assessments
            }
        except Exception as e:
            return {"error": str(e)}



# # run: python -m backend.src.langgraph_rag.guardrails.bedrock_guardrails
# if __name__ == "__main__":
#     from ..utils.config_utils import BaseConfig
#     global_config = BaseConfig()
#     bedrock_guardrails = BedrockGuardrails(global_config= global_config)
#     query = "Cầu vồng có mấy màu"
#     # # Kiểm tra đầu vào trước khi truy vấn
#     result = bedrock_guardrails.apply_guardrail(
#         text=query,
#         source_type="INPUT"
#     )
#     print(f"result: {result}")
#     print(result['assessments'][-1]['invocationMetrics']['guardrailCoverage']['textCharacters']['total'])