import boto3
from instructor import from_bedrock, Mode
from qdrant_client.models import Filter, Condition
from pydantic import BaseModel

from .base import BaseFilterConfig, FilterConfig
from ..utils.config_utils import BaseConfig
from ..utils.logger_utils import get_logger

logger = get_logger(__name__)


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

class BedrockFilter(BaseFilterConfig):
    
    def __init__(self, global_config = None):
        self.global_config = global_config
        super().__init__(global_config)

        self._init_filter_llm_config()
        self.llm_filter_client = self._setup_llm_client()
    
    def _init_filter_llm_config(self):
        config_dict = self.global_config.__dict__
        
        config_dict['filter_llm_name'] = self.global_config.filter_llm_name
        config_dict['region_name'] = "us-east-1"
    
        self.llm_config = FilterConfig.from_dict(config_dict=config_dict)
        # logger.info(f"[BedrockLLM] Config: {self.llm_config}")


    def _setup_llm_client(self):
        bedrock_runtime = boto3.client("bedrock-runtime", region_name=self.llm_config.region_name)
        return from_bedrock(
            client=bedrock_runtime,
            model=self.llm_config.filter_llm_name,
            mode=Mode.BEDROCK_JSON,
        )
    
    def automate_filtering(self, user_query, formatted_indexes, filter_prompt) -> Filter:
        response = self.llm_filter_client.messages.create(
        response_model=QdrantFilterWrapper,
        messages=[
            {"role": "user", "content": filter_prompt.strip()},
            {"role": "assistant", "content": "Đã hiểu. Tôi sẽ tuân thủ các quy tắc."},
            {"role": "user", "content": f"<query>{user_query}</query>\n<indexes>\n{formatted_indexes}\n</indexes>"}
            ]
        )

        return response.to_qdrant_filter()


# # run: python -m langgraph_rag.filtering.bedrock_filter
# if __name__ == "__main__":
#     from ..utils.config_utils import BaseConfig
#     from .test_filter import *
#     global_config = BaseConfig()
#     bedrock_filter = BedrockFilter(global_config= global_config)
#     q = "Thủ tục đăng ký tạm trú gồm những bước nào?"
#     r = bedrock_filter.automate_filtering(user_query=q, filter_prompt= FILTER_PROMPT_PROCEDURE, formatted_indexes= FORMATTED_INDEXES_PROCEDURE)