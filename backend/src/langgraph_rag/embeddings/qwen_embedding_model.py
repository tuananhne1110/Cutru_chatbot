from typing import List, Optional, Union
from copy import deepcopy
from sentence_transformers import SentenceTransformer
import tqdm
from .base import BaseEmbeddingModelConfig, EmbeddingModelConfig
from ..utils.config_utils import BaseConfig
from ..utils.logger_utils import get_logger



logger = get_logger(__name__)

class QwenEmbeddingModel(BaseEmbeddingModelConfig):
    def __init__(self, global_config: Optional[BaseConfig] = None, embedding_model_name: Optional[str] = None) -> None:
        super().__init__(global_config=global_config)

        if embedding_model_name is not None:
            self.embedding_model_name = embedding_model_name
            logger.debug(f"Overriding {self.__class__.__name__}'s embedding_model_name with: {self.embedding_model_name}")
            
            
        self._init_embedding_config()

        logger.debug(f"Initializing {self.__class__.__name__}'s embedding model with params: {self.embedding_config.model_init_params}")

        self.embedding_model = SentenceTransformer(**self.embedding_config.model_init_params)
        self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()


    def _init_embedding_config(self) -> None:
        config_dict = {
            "embedding_model_name": self.embedding_model_name,
            "norm": self.global_config.embedding_return_as_normalized,

            "model_init_params": {
                "model_name_or_path": self.embedding_model_name,
                # "trust_remote_code": True,
                # "device": self.global_config.embedding_device,
                # 'device_map': "auto",  # added this line to use multiple GPUs
                # "torch_dtype": self.global_config.embedding_model_dtype,
                # **kwargs
            },
            "encode_params": {
                "max_length": self.global_config.embedding_max_seq_len,  # 32000 from official example,
                "instruction": "",
                "batch_size": self.global_config.embedding_batch_size,
                "num_workers": 32,
                "prompt_name": "query"
            },
        }

        self.embedding_config = EmbeddingModelConfig.from_dict(config_dict=config_dict)
        logger.debug(f"Init {self.__class__.__name__}'s embedding_config: {self.embedding_config}")
    
    def batch_encode(self, texts: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        Encode 1 hoặc nhiều câu bằng SentenceTransformer (Qwen3-Embedding).
        Tự lấy tham số từ self.embedding_config.encode_params.
        """
        params = deepcopy(self.embedding_config.encode_params)
        params["normalize_embeddings"] = self.embedding_config.norm
        params["show_progress_bar"] = isinstance(texts, list) and len(texts) > params.get("batch_size", 32)

        # Chuẩn bị input
        single_input = isinstance(texts, str)
        input_texts = [texts.lower()] if single_input else [t.lower() for t in texts]

        # Gọi encode
        emb = self.embedding_model.encode(input_texts, **params)

        # Trả về đúng định dạng
        return emb[0] if single_input else emb
    

# # run: python -m backend.src.langgraph_rag.embeddings.qwen_embedding_model
# if __name__ == "__main__":
#     from ..utils.config_utils import BaseConfig
#     global_config = BaseConfig()
#     model = QwenEmbeddingModel(global_config= global_config)

#     # Encode 1 câu
#     emb1 = model.batch_encode("Xin chào, hôm nay trời đẹp quá")

#     # Encode nhiều câu
#     sentences = [
#         "Xin chào, hôm nay trời đẹp quá",
#         "Hôm nay là một ngày tuyệt vời để đi dạo"
#     ]

#     import numpy as np
#     emb_list = np.array(model.batch_encode(sentences))

#     print(emb_list.shape)
#     print(emb_list.nbytes)
#     print(emb_list.dtype)

