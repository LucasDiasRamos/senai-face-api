import cv2
import numpy as np
from insightface.app import FaceAnalysis

from app.config import FACE_CTX_ID


class FaceEngineError(ValueError):
    code = "face_engine_error"
    face_count = None


class InvalidImageError(FaceEngineError):
    code = "invalid_image"
    face_count = 0


class NoFaceFoundError(FaceEngineError):
    code = "no_face"
    face_count = 0


class MultipleFacesFoundError(FaceEngineError):
    code = "multiple_faces"

    def __init__(self, face_count: int):
        self.face_count = face_count
        super().__init__(f"Mais de um rosto encontrado: {face_count}")


class FaceEngine:
    def __init__(self):
        self.app = FaceAnalysis(
            name="buffalo_l",
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"]
        )
        self.app.prepare(ctx_id=FACE_CTX_ID, det_size=(640, 640))
        # ctx_id=-1 = CPU
        # ctx_id=0 = GPU, caso use onnxruntime-gpu depois

    def get_embedding(self, image_bytes: bytes):
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if img is None:
            raise InvalidImageError("Imagem inválida")

        faces = self.app.get(img)
        face_count = len(faces)

        if face_count == 0:
            raise NoFaceFoundError("Nenhum rosto encontrado")

        if face_count > 1:
            raise MultipleFacesFoundError(face_count)

        face = faces[0]

        embedding = face.embedding
        embedding = embedding / np.linalg.norm(embedding)

        return embedding

    def compare(self, embedding_a, embedding_b):
        return float(np.dot(embedding_a, embedding_b))
