from typing import List, Union
import boto3
import json
from .base import BaseEmbedding
from config.configs import EmbeddingModelConfig


class BedrockEmbedding(BaseEmbedding):
    """Amazon Bedrock Titan Text Embedding implementation (tương đương SentenceTransformerEmbedding)"""

    def __init__(self, config: EmbeddingModelConfig):

        print(config.model_id)

        self.config = config
        self.bedrock_client = boto3.client(service_name='bedrock-runtime')


    def initialize(self) -> bool:
        """Titan không cần tải model, chỉ kiểm tra kết nối"""
        try:
            # self.logger.info(f"Khởi tạo Bedrock Embedding với model_id={self.config.output_dimension}, dim={self.config.output_dimension}")
            return True
        except Exception as e:
            # self.logger.error(f"Lỗi khởi tạo: {e}")
            return False

    def encode(self, texts: Union[str, List[str]], normalize: bool = None) -> Union[List[float], List[List[float]]]:
        """Encode text thành vector embedding từ Bedrock Titan"""
        normalize = normalize if normalize is not None else self.config.normalize
        is_single = isinstance(texts, str)
        inputs = [texts] if is_single else texts

        embeddings = []
        for text in inputs:
            try:
                payload = {
                    "inputText": text,
                    "dimensions": self.config.output_dimension,
                    "normalize": normalize,
                    "embeddingTypes": ["float"]
                }
                res = self.bedrock_client.invoke_model(
                    modelId=self.config.model_id,
                    body=json.dumps(payload),
                    accept="application/json",
                    contentType="application/json"
                )
                body = json.loads(res['body'].read())
                embeddings.append(body.get("embedding", []))
            except Exception as e:
                embeddings.append([])

        return embeddings[0] if is_single else embeddings

    def get_dimension(self) -> int:
        return self.config.output_dimension

