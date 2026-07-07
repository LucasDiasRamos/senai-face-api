import onnxruntime as ort

print("ONNX Runtime version:", ort.__version__)
print("Available providers:", ort.get_available_providers())

providers = ort.get_available_providers()

if "CUDAExecutionProvider" in providers:
    print("CUDAExecutionProvider aparece na lista.")
else:
    print("CUDAExecutionProvider NÃO aparece na lista.")

print("\nImportante:")
print("Se o InsightFace mostrar 'Applied providers: CPUExecutionProvider',")
print("então o CUDA provider existe, mas falhou ao carregar alguma DLL.")