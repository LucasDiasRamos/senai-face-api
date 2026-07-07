import cv2
import numpy as np

from insightface.app import FaceAnalysis
from app.database import init_db, load_all_embeddings


HIGH_THRESHOLD = 0.65
MEDIUM_THRESHOLD = 0.50


def normalize_embedding(embedding):
    return embedding / np.linalg.norm(embedding)


def compare_embeddings(embedding_a, embedding_b):
    return float(np.dot(embedding_a, embedding_b))


def find_best_match(current_embedding, registered_faces):
    best_match = None
    best_score = -1.0

    for person in registered_faces:
        score = compare_embeddings(
            current_embedding,
            person["embedding"]
        )

        if score > best_score:
            best_score = score
            best_match = person

    return best_match, best_score


def get_label(best_match, best_score):
    if best_match is None:
        return "Sem cadastro", (0, 0, 255)

    if best_score >= HIGH_THRESHOLD:
        return f"{best_match['name']} ({best_score:.2f})", (0, 255, 0)

    if best_score >= MEDIUM_THRESHOLD:
        return f"Possivel: {best_match['name']} ({best_score:.2f})", (0, 255, 255)

    return f"Desconhecido ({best_score:.2f})", (0, 0, 255)


def main():
    print("Inicializando banco...")
    init_db()

    print("Carregando faces cadastradas...")
    registered_faces = load_all_embeddings()

    if not registered_faces:
        print("Nenhuma face cadastrada no banco.")
        print("Cadastre primeiro uma pessoa usando o endpoint /enroll.")
        return

    print(f"Faces cadastradas carregadas: {len(registered_faces)}")

    print("Carregando modelo InsightFace...")
    face_app = FaceAnalysis(
        name="buffalo_l",
        providers=["CUDAExecutionProvider", "CPUExecutionProvider"]
    )
    
    face_app.prepare(ctx_id=0, det_size=(640, 640))
    # ctx_id=-1 usa CPU
    # ctx_id=0 tenta usar GPU, se estiver configurado

    print("Abrindo câmera...")
    cap = cv2.VideoCapture(1)

    if not cap.isOpened():
        print("Erro: não foi possível abrir a câmera.")
        print("Tente trocar cv2.VideoCapture(0) para cv2.VideoCapture(1).")
        return

    print("Câmera aberta.")
    print("Pressione Q para sair.")
    print("Pressione R para recarregar os cadastros do banco.")

    while True:
        ret, frame = cap.read()

        if not ret:
            print("Erro ao capturar imagem da câmera.")
            break

        faces = face_app.get(frame)

        for face in faces:
            bbox = face.bbox.astype(int)
            x1, y1, x2, y2 = bbox

            current_embedding = normalize_embedding(face.embedding)

            best_match, best_score = find_best_match(
                current_embedding,
                registered_faces
            )

            label, color = get_label(best_match, best_score)

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                color,
                2
            )

            cv2.putText(
                frame,
                label,
                (x1, max(y1 - 10, 30)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2
            )

        cv2.putText(
            frame,
            "Q: sair | R: recarregar cadastros",
            (20, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )

        cv2.imshow("Senia Face Recognition", frame)

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break

        if key == ord("r"):
            registered_faces = load_all_embeddings()
            print(f"Cadastros recarregados: {len(registered_faces)}")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()