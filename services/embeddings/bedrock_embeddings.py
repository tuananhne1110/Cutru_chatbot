from typing import List, Union, Optional
import boto3
import json


class BedrockEmbeddingConfig:
    """Cấu hình cho Bedrock Embedding"""
    def __init__(self, model_id: str, region_name: str, output_dimension: int = 1536, normalize: bool = True):
        self.model_id = model_id
        self.output_dimension = output_dimension
        self.normalize = normalize
        self.region_name = region_name

class BedrockEmbedding:
    """Amazon Bedrock Titan Text Embedding implementation"""

    def __init__(self, config: BedrockEmbeddingConfig):
        self.config = config
        self.bedrock_client = boto3.client(service_name='bedrock-runtime', region_name = config.region_name)

    def initialize(self) -> bool:
        pass

    def encode(
        self,
        texts: Union[str, List[str]],
        normalize: Optional[bool] = None
    ) -> Union[List[float], List[List[float]]]:
        """
        Encode văn bản thành vector embedding từ Bedrock Titan.

        Args:
            texts (str or List[str]): Đầu vào là một chuỗi hoặc danh sách chuỗi.
            normalize (bool, optional): Có chuẩn hoá vector hay không. Mặc định theo config.

        Returns:
            List[float] nếu input là str,
            List[List[float]] nếu input là List[str].
        """
        is_single = isinstance(texts, str)
        inputs = [texts] if is_single else texts
        normalize = self.config.normalize if normalize is None else normalize

        embeddings = []
        for text in inputs:
            try:
                payload = {
                    "inputText": text,
                    "dimensions": self.config.output_dimension,
                    "normalize": normalize,
                    "embeddingTypes": ["float"]
                }
                response = self.bedrock_client.invoke_model(
                    modelId=self.config.model_id,
                    body=json.dumps(payload),
                    accept="application/json",
                    contentType="application/json"
                )
                body = json.loads(response['body'].read())
                embedding = body.get("embedding", [])
                embeddings.append(embedding)
            except Exception as e:
                print(f"Lỗi encode văn bản: {e}")
                embeddings.append([])

        return embeddings[0] if is_single else embeddings

    def get_dimension(self) -> int:
        """Lấy dimension của vector"""
        return self.config.output_dimension
