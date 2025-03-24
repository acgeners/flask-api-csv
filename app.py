from flask import Flask, request, jsonify, Response
import os
# from code_sup import new_file, ref_file
from transform_data import main  # Importa a função de processamento
# import unicodedata
# import re

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER)

# Certifique-se de que a pasta de uploads existe
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# # Função para normalizar strings: converte para minúsculas e remove acentuação
# def normalize_str(s):
#     s = s.lower()
#     nfkd_form = unicodedata.normalize('NFKD', s)
#     return ''.join(c for c in nfkd_form if not unicodedata.combining(c))
#
# def name_eval(name):
#     """
#     Pontua o nome do arquivo somando 1 para cada ocorrência de uma palavra positiva
#     (considerando limites de palavra) e subtraindo 1 para cada palavra negativa.
#     """
#     clean_name = normalize_str(name)
#     score = 0
#     # Pontua cada ocorrência de palavras positivas
#     for word in ref_file:
#         if re.search(r'\b' + re.escape(word) + r'\b', clean_name):
#             score += 1
#     # Subtrai pontos para palavras negativas
#     for word in new_file:
#         if re.search(r'\b' + re.escape(word) + r'\b', clean_name):
#             score -= 1
#     return score
#
# def define_file_roles(files_data):
#     """
#     Recebe uma lista com os dados dos arquivos (nome original e caminho completo)
#     e, utilizando a função name_eval e regras de desempate, define qual arquivo é de referência
#     e qual é o novo.
#     Retorna uma tupla com (file_ref_name, ref_name, file_new_name, new_name).
#     """
#     candidate1 = files_data[0]
#     candidate2 = files_data[1]
#
#     # Utiliza o nome original para a avaliação
#     score1 = name_eval(candidate1["filename"])
#     score2 = name_eval(candidate2["filename"])
#
#     # Em caso de empate, verifica as palavras positivas e negativas para desempate
#     if score1 == score2:
#         # Verifica a presença de palavras positivas
#         tem_pos_candidate1 = any(re.search(r'\b' + re.escape(word) + r'\b', normalize_str(candidate1["filename"])) for word in ref_file)
#         tem_pos_candidate2 = any(re.search(r'\b' + re.escape(word) + r'\b', normalize_str(candidate2["filename"])) for word in ref_file)
#         if tem_pos_candidate1 and not tem_pos_candidate2:
#             score1 += 1
#         elif tem_pos_candidate2 and not tem_pos_candidate1:
#             score2 += 1
#         else:
#             # Se ainda houver empate, verifica a presença de palavras negativas
#             # O arquivo que NÃO apresentar palavras negativas é preferido como referência
#             tem_neg_candidate1 = any(re.search(r'\b' + re.escape(word) + r'\b', normalize_str(candidate1["filename"])) for word in new_file)
#             tem_neg_candidate2 = any(re.search(r'\b' + re.escape(word) + r'\b', normalize_str(candidate2["filename"])) for word in new_file)
#             if tem_neg_candidate1 and not tem_neg_candidate2:
#                 score2 += 1  # candidate1 contém palavra negativa, favorece candidate2
#             elif tem_neg_candidate2 and not tem_neg_candidate1:
#                 score1 += 1  # candidate2 contém palavra negativa, favorece candidate1
#
#     # Define qual é o arquivo de referência com base na pontuação
#     if score1 > score2:
#         file_ref_name = candidate1["filepath"]
#         ref_name = candidate1["filename"]
#         file_new_name = candidate2["filepath"]
#         new_name = candidate2["filename"]
#     elif score2 > score1:
#         file_ref_name = candidate2["filepath"]
#         ref_name = candidate2["filename"]
#         file_new_name = candidate1["filepath"]
#         new_name = candidate1["filename"]
#     else:
#         print("Ambos os arquivos têm pontuação igual. Verifique os nomes manualmente.")
#         file_ref_name = candidate1["filepath"]
#         ref_name = candidate1["filename"]
#         file_new_name = candidate2["filepath"]
#         new_name = candidate2["filename"]
#
#     return file_ref_name, ref_name, file_new_name, new_name
#


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

    # # Define os papéis dos arquivos (arquivo de referência e arquivo novo)
    # file_ref_name, ref_name, file_new_name, new_name = define_file_roles(files_data)
        # Definir papéis dos arquivos com base no prefixo "ref_data"
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

    return Response(result, mimetype='application/json')


if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 10000))  # Pega a porta definida pelo Render
    app.run(host="0.0.0.0", port=PORT)
