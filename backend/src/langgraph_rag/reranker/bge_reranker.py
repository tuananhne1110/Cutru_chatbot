import numpy as np
import torch
from typing import List, Tuple, Optional
from transformers import AutoTokenizer, AutoModelForSequenceClassification, BitsAndBytesConfig
from .base import BaseRerankerModelConfig, RerankerModelConfig

from ..utils.config_utils import BaseConfig
from ..utils.logger_utils import get_logger


logger = get_logger(__name__)


# floating point 32
# class BGEReranker(BaseRerankerModelConfig):
#     """BGE Reranker implementation"""
    
#     def __init__(self, global_config: Optional[BaseConfig] = None, reranker_model_name: Optional[str] = None) -> None:
#         super().__init__(global_config=global_config)

#         if reranker_model_name is not None:
#             self.reranker_model_name = reranker_model_name
#             logger.debug(f"Overriding {self.__class__.__name__}'s reranker_model_name with: {self.reranker_model_name}")
            
            
#         self._init_reranker_config()

#         logger.debug(f"Initializing {self.__class__.__name__}'s reranker model with params: {self.reranker_config.model_init_params}")

#         # init tokenizer & model dùng đúng tên tham số
#         self.tokenizer = AutoTokenizer.from_pretrained(
#             **self.reranker_config.tokenizer_init_params
#         )
#         self.reranker_model = AutoModelForSequenceClassification.from_pretrained(
#             **self.reranker_config.model_init_params
#         )

#         device = self.reranker_config.runtime_params["device"]
#         self.reranker_model.to(device=device).eval()


#     def _init_reranker_config(self) -> None:
#         """
#         Dựng cấu hình reranker đúng theo các tham số bạn đã định nghĩa trong global_config:
#           - reranker_model_name, reranker_device, trust_remote_code, use_fp16
#           - max_length, truncation, batch_size, apply_sigmoid, top_k
#         """
#         # Lấy tham số từ global_config (đã có sẵn trong file config của bạn)
#         config_dict = {
#             "reranker_model_name": self.global_config.reranker_model_name,

#             "tokenizer_init_params": {
#                 "pretrained_model_name_or_path": self.global_config.reranker_model_name,
#             },
#             "model_init_params": {
#                 "pretrained_model_name_or_path": self.global_config.reranker_model_name,
#             },

#             "runtime_params": {
#                 "device": self.global_config.reranker_device,
#             },

#             "encode_params": {
#                 "max_length": int(self.global_config.max_length),
#                 "batch_size": int(self.global_config.batch_size),
#                 "apply_sigmoid": bool(self.global_config.apply_sigmoid),
#                 "top_k": int(self.global_config.top_k),
#             },
#         }

#         self.reranker_config = RerankerModelConfig.from_dict(config_dict=config_dict)
#         logger.debug(f"Init {self.__class__.__name__}'s reranker_config: {self.reranker_config}")

#     @torch.inference_mode()
#     def rerank(self, query: str, documents: List[str], top_k: Optional[int] = None) -> List[Tuple[str, float]]:
#         """Rerank documents trả về [(doc, score)] đã sắp xếp giảm dần."""
#         if not hasattr(self, "reranker_model") or self.reranker_model is None or self.tokenizer is None:
#             raise RuntimeError("Reranker model chưa được khởi tạo.")

#         if not documents:
#             return []

#         enc = self.reranker_config.encode_params
#         runtime = self.reranker_config.runtime_params
#         device = runtime["device"]

#         bs = enc["batch_size"]
#         mx = enc["max_length"]
#         use_sigmoid = enc["apply_sigmoid"]
#         k = int(top_k) if top_k is not None else int(enc["top_k"])

#         scores: List[float] = []
#         # Duyệt theo batch
#         for start in range(0, len(documents), bs):
#             batch_docs = documents[start:start + bs]

#             # Chuẩn nhất với HF: truyền text & text_pair riêng để tokenizer pair chính xác
#             inputs = self.tokenizer(
#                 text=[query] * len(batch_docs),
#                 text_pair=batch_docs,
#                 truncation= True,
#                 padding=True,
#                 max_length=mx,
#                 return_tensors="pt",
#             ).to(device)

#             outputs = self.reranker_model(**inputs)              # logits: (batch, 1) đối với BGE-reranker
#             logits = outputs.logits.squeeze(-1)                  # -> (batch,)
#             if use_sigmoid:
#                 batch_scores = torch.sigmoid(logits).float().tolist()
#             else:
#                 batch_scores = logits.float().tolist()
#             scores.extend(batch_scores)

#         # Sắp xếp & trả top-k
#         np_scores = np.asarray(scores, dtype=float)
#         order = np.argsort(-np_scores)[:min(k, len(documents))]
#         return [(documents[i], float(np_scores[i])) for i in order]

# Int 8


class BGEReranker(BaseRerankerModelConfig):
    """BGE Reranker implementation with optional INT8/8-bit quantization"""

    def __init__(self, global_config: Optional[BaseConfig] = None, reranker_model_name: Optional[str] = None) -> None:
        super().__init__(global_config=global_config)

        if reranker_model_name is not None:
            self.reranker_model_name = reranker_model_name
            logger.debug(f"Overriding {self.__class__.__name__}'s reranker_model_name with: {self.reranker_model_name}")

        # ==== NEW: đọc flag quantization từ global_config (nếu có) ====
        self._quantize_int8: bool = bool(getattr(self.global_config, "reranker_quantize_int8", False))
        # "pytorch_dynamic" | "bitsandbytes"
        self._quant_backend: str = str(getattr(self.global_config, "reranker_quant_backend", "pytorch_dynamic")).lower()

        self._init_reranker_config()

        logger.debug(f"Initializing {self.__class__.__name__}'s reranker model with params: {self.reranker_config.model_init_params} | "
                     f"quantize_int8={self._quantize_int8}, backend={self._quant_backend}")

        # === init tokenizer ===
        self.tokenizer = AutoTokenizer.from_pretrained(
            **self.reranker_config.tokenizer_init_params
        )

        # === init model (tùy backend để gắn tham số load) ===
        # Với bitsandbytes 8-bit: đã chèn load_in_8bit & device_map ở _init_reranker_config()
        self.reranker_model = AutoModelForSequenceClassification.from_pretrained(
            **self.reranker_config.model_init_params
        )

        # === Áp dụng quantization động INT8 trên CPU (PyTorch) nếu chọn backend này ===
        if self._quantize_int8 and self._quant_backend == "pytorch_dynamic":
            import torch.nn as nn
            # model phải ở CPU để quantize_dynamic trả về qmodel trên CPU
            self.reranker_model.to("cpu")
            self.reranker_model = torch.ao.quantization.quantize_dynamic(
                self.reranker_model,
                {nn.Linear},
                dtype=torch.qint8
            ).eval()
            # ép runtime device về cpu cho nhất quán
            self.reranker_config.runtime_params["device"] = "cpu"
            logger.info(f"[{self.__class__.__name__}] Applied PyTorch dynamic INT8 quantization on CPU.")
        else:
            # không quant INT8 CPU -> cứ eval bình thường
            self.reranker_model.eval()

        # cuối cùng move theo runtime device (bitsandbytes có thể là cuda qua device_map=auto)
        device = self.reranker_config.runtime_params["device"]
        try:
            self.reranker_model.to(device=device)
        except Exception:
            # với bitsandbytes load_in_8bit + device_map="auto", model đã phân mảnh trên GPU;
            # .to(device) có thể không cần thiết hoặc sẽ raise -> bỏ qua
            pass

    def _init_reranker_config(self) -> None:
        """
        Dựng cấu hình reranker từ global_config + chèn tham số quantization nếu có.
        """
        # mặc định lấy device từ config
        desired_device = getattr(self.global_config, "reranker_device", "cpu")

        model_init_params = {
            "pretrained_model_name_or_path": self.global_config.reranker_model_name,
        }

        # ==== NEW: chèn tham số theo backend ====
        if self._quantize_int8 and self._quant_backend == "bitsandbytes_error":

            bnb_cfg = BitsAndBytesConfig(load_in_8bit=True)
            model_init_params.update({
                "quantization_config": bnb_cfg,
                "device_map": "auto",
            })
            # nếu có CUDA thì set mặc định device là 'cuda', còn không để 'cpu' cũng được (device_map auto quyết định)
            if torch.cuda.is_available():
                desired_device = "cuda"
        elif self._quantize_int8 and self._quant_backend == "pytorch_dynamic":
            # INT8 động trên CPU -> device phải là cpu
            desired_device = "cpu"
        else:
            # không quant -> giữ nguyên desired_device
            pass

        config_dict = {
            "reranker_model_name": self.global_config.reranker_model_name,
            "tokenizer_init_params": {
                "pretrained_model_name_or_path": self.global_config.reranker_model_name,
            },
            "model_init_params": model_init_params,
            "runtime_params": {
                "device": desired_device,
            },
            "encode_params": {
                "max_length": int(getattr(self.global_config, "max_length", 512)),
                "batch_size": int(getattr(self.global_config, "batch_size", 16)),
                "apply_sigmoid": bool(getattr(self.global_config, "apply_sigmoid", False)),
                "top_k": int(getattr(self.global_config, "top_k", 10)),
            },
        }

        self.reranker_config = RerankerModelConfig.from_dict(config_dict=config_dict)
        logger.debug(f"Init {self.__class__.__name__}'s reranker_config: {self.reranker_config}")

    @torch.inference_mode()
    def rerank(self, query: str, documents: List[str], top_k: Optional[int] = None) -> List[Tuple[str, float]]:
        """Rerank documents trả về [(doc, score)] đã sắp xếp giảm dần."""
        if not hasattr(self, "reranker_model") or self.reranker_model is None or self.tokenizer is None:
            raise RuntimeError("Reranker model chưa được khởi tạo.")
        if not documents:
            return []

        enc = self.reranker_config.encode_params
        runtime = self.reranker_config.runtime_params
        device = runtime["device"]

        bs = enc["batch_size"]
        mx = enc["max_length"]
        use_sigmoid = enc["apply_sigmoid"]
        k = int(top_k) if top_k is not None else int(enc["top_k"])

        scores: List[float] = []

        for start in range(0, len(documents), bs):
            batch_docs = documents[start:start + bs]

            # Tokenizer đúng chuẩn text/text_pair
            inputs = self.tokenizer(
                text=[query] * len(batch_docs),
                text_pair=batch_docs,
                truncation=True,
                padding=True,
                max_length=mx,
                return_tensors="pt",
            )

            # Với bitsandbytes load_in_8bit + device_map="auto":
            #   - model có thể nằm trên nhiều GPU; tốt nhất chuyển input sang cùng device của first param
            # Với pytorch_dynamic (CPU): device="cpu"
            try:
                # nếu model có param() thì lấy device của tham số đầu tiên
                model_device = next(self.reranker_model.parameters()).device
            except StopIteration:
                model_device = torch.device(device)

            inputs = {k: v.to(model_device) for k, v in inputs.items()}

            outputs = self.reranker_model(**inputs)          # logits: (batch, 1) for BGE reranker
            logits = outputs.logits.squeeze(-1)              # -> (batch,)

            if use_sigmoid:
                batch_scores = torch.sigmoid(logits).float().tolist()
            else:
                batch_scores = logits.float().tolist()
            scores.extend(batch_scores)

        np_scores = np.asarray(scores, dtype=float)
        order = np.argsort(-np_scores)[:min(k, len(documents))]
        return [(documents[i], float(np_scores[i])) for i in order]



# # run: python -m backend.src.langgraph_rag.reranker.bge_reranker
# if __name__ == "__main__":
#     from ..utils.config_utils import BaseConfig
#     global_config = BaseConfig()
#     reranker = BGEReranker(global_config=global_config)

#     query = "Điều kiện cấp hộ chiếu phổ thông cho công dân Việt Nam là gì?"
#     docs = [
#         "Công dân Việt Nam từ đủ 14 tuổi được cấp hộ chiếu phổ thông có thời hạn 10 năm.",
#         "Giấy khai sinh là giấy tờ hộ tịch do cơ quan nhà nước có thẩm quyền cấp cho cá nhân khi sinh ra.",
#         "Hộ chiếu phổ thông được cấp cho công dân Việt Nam để xuất cảnh, nhập cảnh; người từ đủ 14 tuổi có thể làm hộ chiếu gắn chíp.",
#         "Thủ tục cấp lại CCCD khi bị mất gồm tờ khai và thông tin sinh trắc học.",
#         "Visa là giấy tờ do cơ quan có thẩm quyền của nước ngoài cấp cho người nước ngoài nhập cảnh."
#     ]

#     results = reranker.rerank(query, docs)
#     for rank, (doc, score) in enumerate(results, 1):
#         print(f"#{rank} | score={score:.4f} | {doc}")
