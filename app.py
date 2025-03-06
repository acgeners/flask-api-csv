from flask import Flask, request, jsonify, Response
import os
from transform_data import main  # Importa a função de processamento

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/process", methods=["POST"])
def process_file():
    print("Requisição recebida!")  # 🚀 Confirma que a requisição chegou

    if not request.files:
        print("Nenhum arquivo recebido.")  # 🛑 Debug se não houver arquivo
        return jsonify({"error": "No file was provided."}), 400

    # Pegando o primeiro arquivo recebido, independentemente da chave
    uploaded_file = next(iter(request.files.values()))

    file_path = os.path.join(UPLOAD_FOLDER, uploaded_file.filename)
    new_path = uploaded_file.filename

    uploaded_file.save(file_path)
    print(f"Arquivo salvo em {file_path}")  # ✅ Confirmação de salvamento

    result = main(file_path, new_path)
    print("Arquivo processado!")  # 🚀 Confirma que processou o CSV

    # Retornar JSON diretamente usando jsonify
    return result

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 10000))  # Pega a porta definida pelo Render
    app.run(host="0.0.0.0", port=PORT)
