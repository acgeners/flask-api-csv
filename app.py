from flask import Flask, request, jsonify, Response
import os
from transform_data import main  # Importa a função de processamento
from io import StringIO
import pandas as pd

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER)

# Certifique-se de que a pasta de uploads existe
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def csv_to_json(csv_string):
    try:
        # Lê o CSV a partir de uma string
        df = pd.read_csv(StringIO(csv_string))
        # Converte o DataFrame para uma lista de dicionários
        return df.to_dict(orient="records")
    except Exception as e:
        return {"error": f"Erro ao converter CSV para JSON: {str(e)}"}


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

    if isinstance(result, dict) and "error" in result:
        return jsonify(result), 500

        # Converte o CSV para JSON
    json_data = csv_to_json(result)
    if isinstance(json_data, dict) and "error" in json_data:
        return jsonify(json_data), 500

    return jsonify({"result": json_data})

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 10000))  # Pega a porta definida pelo Render
    app.run(host="0.0.0.0", port=PORT)
