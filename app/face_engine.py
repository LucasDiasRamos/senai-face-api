import cv2
import numpy as np
from insightface.app import FaceAnalysis


class FaceEngine:
    def __init__(self):
        self.app = FaceAnalysis(
            name="buffalo_l",
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"]
        )
        self.app.prepare(ctx_id=0, det_size=(640, 640))
        # ctx_id=-1 = CPU
        # ctx_id=0 = GPU, caso use onnxruntime-gpu depois

    def get_embedding(self, image_bytes: bytes):
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if img is None:
            raise ValueError("Imagem inválida")

        faces = self.app.get(img)

        if len(faces) == 0:
            raise ValueError("Nenhum rosto encontrado")

        if len(faces) > 1:
            raise ValueError("Mais de um rosto encontrado")

        face = faces[0]

        embedding = face.embedding
        embedding = embedding / np.linalg.norm(embedding)

        return embedding

    def compare(self, embedding_a, embedding_b):
        return float(np.dot(embedding_a, embedding_b))
