from flask import Flask, request, jsonify, Response
import os
from transform_data import main  # Importa a função de processamento

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"

# Certifique-se de que a pasta de uploads existe
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/process", methods=["POST"])
def process_file():
    print("Requisição recebida!")  # 🚀 Confirma que a requisição chegou

    if not request.files:
        print("Nenhum arquivo recebido.")  # 🛑 Debug se não houver arquivo
        return jsonify({"error": "No file was provided."}), 400

    # Armazena os arquivos enviados como dicionários contendo o nome original e o caminho completo
    files_data = []
    for file_key in request.files:
        uploaded_file = request.files[file_key]
        original_filename = uploaded_file.filename
        file_path = os.path.join(UPLOAD_FOLDER, original_filename)
        uploaded_file.save(file_path)
        print(f"Arquivo {original_filename} salvo em {file_path}")
        files_data.append({"filename": original_filename, "filepath": file_path})

    if len(files_data) != 2:
        return jsonify({"error": "É necessário enviar exatamente 2 arquivos."}), 400

    file_ref_name, ref_name, file_new_name, new_name = None, None, None, None

    for file in files_data:
        if file["filename"].startswith("ref_data"):
            file_ref_name, ref_name = file["filepath"], file["filename"]
        else:
            file_new_name, new_name = file["filepath"], file["filename"]

    # Verificar se ambos os arquivos foram corretamente atribuídos
    if not file_ref_name or not file_new_name:
        return jsonify({
                           "error": "Não foi possível identificar os arquivos corretamente. Certifique-se de que um arquivo começa com 'ref_data'."}), 400

    print("Arquivo de referência:", file_ref_name)
    print("Arquivo novo:", file_new_name)

    # Chama a função principal de processamento passando os arquivos e os nomes
    result = main(file_ref_name, file_new_name, ref_name, new_name)
    print("Arquivos processados!")

    print("Resultado JSON:", result[:500])  # Mostra os primeiros 500 caracteres
    return Response(result, mimetype='application/json')


if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 10000))  # Pega a porta definida pelo Render
    app.run(host="0.0.0.0", port=PORT)
