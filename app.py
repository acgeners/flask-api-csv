from flask import Flask, request, jsonify, Response
import os
# from code_sup import new_file, ref_file
from transform_data import main  # Importa a função de processamento
import unicodedata
import re

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER)

# Certifique-se de que a pasta de uploads existe
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Função para normalizar strings: converte para minúsculas e remove acentuação
def normalize_str(s):
    s = s.lower()
    nfkd_form = unicodedata.normalize('NFKD', s)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

# Define os nomes esperados (normalizados) para cada arquivo
expected_ref = "modelo_entidade_pessoa"

@app.route("/process", methods=["POST"])
def process_file():
    print("Requisição recebida!")  # 🚀 Confirma que a requisição chegou

    if not request.files:
        print("Nenhum arquivo recebido.")  # 🛑 Debug se não houver arquivo
        return jsonify({"error": "No file was provided."}), 400

    file_ref = None
    file_new = None
    ref_name = None
    new_name = None

    for file_key in request.files:
        uploaded_file = request.files[file_key]
        normalized_filename = normalize_str(uploaded_file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, uploaded_file.filename)
        uploaded_file.save(file_path)
        print(f"Arquivo {uploaded_file.filename} salvo em {file_path}")

        # Verifica se o nome contém "arquivo_modelo_" seguido de ao menos um caractere
        if re.search(r"arquivo_modelo_.+", normalized_filename):
            file_ref = file_path
            print(f"Atribuído {uploaded_file.filename} à variável file_ref")
        else:
            file_new = file_path
            print(f"Atribuído {uploaded_file.filename} à variável file_new")

    # # Itera sobre os arquivos enviados e os salva
    # for file_key in request.files:
    #     uploaded_file = request.files[file_key]
    #     # Normaliza o nome do arquivo
    #     filename_norm = normalize_str(uploaded_file.filename)
    #     file_path = os.path.join(UPLOAD_FOLDER, uploaded_file.filename)
    #     uploaded_file.save(file_path)
    #     print(f"Arquivo {uploaded_file.filename} salvo em {file_path}")

        # # Verifica qual lista de palavras-chave corresponde ao nome do arquivo
        # if any(keyword in filename_norm for keyword in ref_file):
        #     file_ref = file_path
        #     ref_name = uploaded_file.filename
        #     print(f"Atribuído {uploaded_file.filename} à variável file_ref")
        # elif any(keyword in filename_norm for keyword in new_file):
        #     file_new = file_path
        #     new_name = uploaded_file.filename
        #     print(f"Atribuído {uploaded_file.filename} à variável file_new")
        # else:
        #     print(f"O arquivo {uploaded_file.filename} não corresponde a nenhuma categoria esperada.")

    # Verifica se ambos os arquivos foram enviados e identificados corretamente
    if not file_ref or not file_new:
        return jsonify({"error": "Um ou ambos os arquivos não foram enviados ou seus nomes não correspondem aos "
                                 "padrões esperados."}), 400

    result = main(file_ref, file_new, ref_name, new_name)
    print("Arquivos processados!")

    return Response(result, mimetype='application/json')

    # Pegando o primeiro arquivo recebido, independentemente da chave
    # uploaded_file = next(iter(request.files.values()))

    # file_path = os.path.join(UPLOAD_FOLDER, uploaded_file.filename)
    # new_path = uploaded_file.filename
    #
    # uploaded_file.save(file_path)
    # print(f"Arquivo salvo em {file_path}")  # ✅ Confirmação de salvamento
    #
    # result = main(file_path, new_path)
    # print("Arquivo processado!")  # 🚀 Confirma que processou o CSV

    # # Define o cabeçalho Content-Type como application/json
    # return Response(result, mimetype='application/json')

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 10000))  # Pega a porta definida pelo Render
    app.run(host="0.0.0.0", port=PORT)
