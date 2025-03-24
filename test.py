for new_col in new_data.columns:
    if new_col in match:
        continue
    ref_embedding = model.encode(ref_col, convert_to_tensor=True)
    new_embedding = model.encode(new_col, convert_to_tensor=True)
    # TODO isso não deveria considerar

    # Verifica se os tipos de dados são compatíveis, ignorando " (range)"
    ref_col_type = ref_types.loc[ref_types['Coluna'] == ref_col, 'Tipo'].values[0] if ref_col in ref_types[
        'Coluna'].values else 'Desconhecido'
    new_col_type = new_types.loc[new_types['Coluna'] == new_col, 'Tipo'].values[0] if new_col in new_types[
        'Coluna'].values else 'Desconhecido'

    # Remove " (range)" dos tipos de dados para a comparação, sem alterar os valores originais
    ref_col_type_cleaned = ref_col_type.replace(" (range)", "")
    name_similarity = util.cos_sim(ref_embedding, new_embedding).item()

    # Permite match se tipos forem iguais ou se um deles for Null e nomes idênticos
    types_compatible = ref_col_type_cleaned == new_col_type
    null_types = "Null" in [ref_col_type, new_col_type]

    # Adiciona lógica para identificar combinações Valor <-> Número
    value_number = (
        (ref_col_type_cleaned in ["Valor", "Número"] and
         (new_col_type in ["Valor", "Número"]))
    )
    if new_col == 'CNAE' and ref_col == 'CNAE':
        print(f"{ref_col}: {ref_col_type}, {ref_col_type_cleaned}.\n x {new_col}: {new_col_type}, {new_col_type}")

    if types_compatible or null_types or value_number:  # Apenas compara colunas do mesmo tipo e nulas
        # Calcula similaridade semântica
        print(f"{new_col} x {ref_col}: name similarity = {name_similarity:.2f}")

        if name_similarity == 1 and (null_types or ref_col_type.endswith("(range)")):  # TODO deixa isso?
            overall_score = 1.0
            candidates.append((ref_col, new_col, overall_score))
            print(
                f"✅ Coluna '{new_col}' adicionada como match direto de '{ref_col}' por similaridade de nome = 1")

# def match_columns(ref_data, new_data, ref_types, new_types, filename1, filename2, threshold=0.59):
#     matched_columns = {}
#     match = {}
#     not_match_new = set(new_data.columns)
#     not_match_ref = set(ref_data.columns)
#     candidates = []
#     model = SentenceTransformer('all-MiniLM-L6-v2')
#     print("\nIniciando correspondência de colunas...")
#
#     for ref_col in ref_data.columns:
#
#         for new_col in new_data.columns:
#             if new_col in match:
#                 continue
#
#             # Verifica se os tipos de dados são compatíveis, ignorando " (range)"
#             ref_col_type = ref_types.loc[ref_types['Coluna'] == ref_col, 'Tipo'].values[0] if ref_col in ref_types[
#                 'Coluna'].values else 'Desconhecido'
#             new_col_type = new_types.loc[new_types['Coluna'] == new_col, 'Tipo'].values[0] if new_col in new_types[
#                 'Coluna'].values else 'Desconhecido'
#
#             # Remove " (range)" dos tipos de dados para a comparação, sem alterar os valores originais
#             ref_col_type_cleaned = ref_col_type.replace(" (range)", "")
#             new_col_type_cleaned = new_col_type.replace(" (range)", "")
#
#             # Permite match se tipos forem iguais ou se um deles for Null e nomes idênticos
#             types_compatible = ref_col_type_cleaned == new_col_type
#             new_types_compatible = ref_col_type_cleaned == new_col_type_cleaned
#             null_types = "Null" in [ref_col_type, new_col_type]
#
#             # Adiciona lógica para identificar combinações Valor <-> Número
#             value_number = (
#                     (ref_col_type_cleaned in ["Valor", "Número"]) and
#                     (new_col_type_cleaned in ["Valor", "Número"]) and
#                     (ref_col_type_cleaned != new_col_type_cleaned)
#             )
#
#             if types_compatible or new_types_compatible or null_types or value_number:  # Apenas compara colunas do mesmo tipo e nulas
#                 # Gera embeddings apenas do nome das colunas
#                 ref_embedding = model.encode(ref_col, convert_to_tensor=True)
#                 new_embedding = model.encode(new_col, convert_to_tensor=True)
#
#                 # Calcula similaridade semântica
#                 name_similarity = util.cos_sim(ref_embedding, new_embedding).item()
#                 print(f"{new_col} x {ref_col}: name similarity = {name_similarity:.2f}")
#
#                 if name_similarity == 1 and (null_types or ref_col_type.endswith("(range)")): #TODO deixa isso?
#                     matched_columns[ref_col] = new_col
#                     match.update({ref_col: new_col})
#                     not_match_new.discard(new_col)
#                     not_match_ref.discard(ref_col)
#                     print(f"✅ Coluna '{new_col}' foi renomeada para '{ref_col}' por similaridade de nome {name_similarity:.2f}")
#                     break  # Se a similaridade for alta o suficiente, já garantimos o match
#
#             if (types_compatible or value_number) and not null_types:
#                 ref_embedding = model.encode(ref_col, convert_to_tensor=True)
#                 new_embedding = model.encode(new_col, convert_to_tensor=True)
#                 name_similarity = util.cos_sim(ref_embedding, new_embedding).item()
#
#                 data_similarity = 0
#                 if new_col in new_data.columns and ref_col in ref_data.columns:
#                     if ref_col_type_cleaned == "Valor":
#                         data_similarity = 1
#
#                     else:  #TODO add regra?
#                         # Cria descrições dos dados das colunas (baseado em amostragem)
#                         ref_description = descrever_coluna_dados(ref_data[ref_col], ref_col)
#                         new_description = descrever_coluna_dados(new_data[new_col], new_col)
#
#                         # Gera embeddings e calcula similaridade semântica entre os dados
#                         ref_data_emb = model.encode(ref_description, convert_to_tensor=True)
#                         new_data_emb = model.encode(new_description, convert_to_tensor=True)
#                         data_similarity = util.cos_sim(ref_data_emb, new_data_emb).item()
#
#                     print(f"{new_col} x {ref_col}: data similarity = {data_similarity:.2f}")
#
#                 if name_similarity == 1:
#                     overall_score = (name_similarity * 0.7) + (data_similarity * 0.3)
#                 else:
#                     overall_score = (name_similarity * 0.4) + (data_similarity * 0.6)
#                 print(f"Score final: {ref_col} x {new_col} = {overall_score}")
#
#                 if overall_score >= threshold:
#                     candidates.append((ref_col, new_col, overall_score))
#
#     # ✅ Após o loop: resolve matches com maior score, sem repetir colunas
#     used_new_cols = set()
#     matched_columns = {}
#
#     candidates.sort(key=lambda x: x[2], reverse=True)
#
#     for ref_col, new_col, score in candidates:
#             if ref_col not in matched_columns and new_col not in used_new_cols:
#                 matched_columns[ref_col] = new_col
#                 used_new_cols.add(new_col)
#                 not_match_new.discard(new_col)
#                 not_match_ref.discard(ref_col)
#                 print(f"✅ Coluna '{new_col}' foi renomeada para '{ref_col}' com score {score:.2f}")
#
#     # Impressão final
#     print("\n\nCorrespondência de colunas concluída!\n\nMatchs realizados (definitivos):")
#     for ref_col, new_col in matched_columns.items():
#         print(f"{ref_col}: {new_col}")
#
#     if not_match_ref:
#         print(f"\nColunas sem correspondência em {filename1}: {not_match_ref}")
#     if not_match_new:
#         print(f"Colunas sem correspondência em {filename2}: {not_match_new}\n")
#
#     return matched_columns

























# import pandas as pd
# from sentence_transformers import SentenceTransformer
# from sklearn.metrics.pairwise import cosine_similarity
# import matplotlib.pyplot as plt
#
#
# # Função para gerar descrição textual de uma coluna
# def descrever_coluna(col_name, col_data, num_exemplos=5):
#     exemplos = col_data.dropna().astype(str).unique()[:num_exemplos]
#     descricao = f"Coluna: {col_name}. Exemplos: {', '.join(exemplos)}. "
#
#     tipo_dado = pd.api.types.infer_dtype(col_data, skipna=True)
#     descricao += f"Tipo de dado inferido: {tipo_dado}. "
#
#     if pd.api.types.is_numeric_dtype(col_data):
#         descricao += f"Média: {col_data.mean():.2f}, Mínimo: {col_data.min()}, Máximo: {col_data.max()}. "
#     elif pd.api.types.is_string_dtype(col_data):
#         descricao += f"Comprimento médio: {col_data.dropna().apply(len).mean():.1f}. "
#
#     return descricao
#
#
# # Carrega CSV
# df = pd.read_csv("teste_comparar.csv")
#
# # Inicializa modelo
# modelo = SentenceTransformer("all-MiniLM-L6-v2")
#
# # Gera descrições e embeddings
# descricoes = [descrever_coluna(col, df[col]) for col in df.columns]
# embeddings = modelo.encode(descricoes)
#
# # Calcula similaridade
# similaridade = cosine_similarity(embeddings)
#
# # Exibe similaridade como tabela
# similaridade_df = pd.DataFrame(similaridade, index=df.columns, columns=df.columns)
# print("\nMapa de Similaridade Semântica entre Colunas:")
# print(similaridade_df)
#
# # Visualiza com heatmap
# plt.figure(figsize=(10, 8))
# plt.imshow(similaridade, cmap='viridis')
# plt.colorbar(label="Similaridade")
# plt.xticks(ticks=range(len(df.columns)), labels=df.columns, rotation=90)
# plt.yticks(ticks=range(len(df.columns)), labels=df.columns)
# plt.title("Similaridade Semântica entre Colunas")
# plt.tight_layout()
# plt.show()
#
#
#
#
#
#
#
#







# import re
#
# def detect_num_range(val, threshold=0.8):
#     """
#     Detecta se uma lista contém valores numéricos e/ou ranges.
#     Retorna um dicionário com a classificação de cada valor.
#     """
#     print("\n🔍 Detectando valores de range de números...")
#
#     def is_num_range(text):
#         """
#         Avalia se um dado representa um número simples ou um range.
#         Retorna True se for um número e True se for um range.
#         """
#         if not isinstance(text, str) or len(text) < 2:
#             return False, False  # Retorna duas flags: (é número, é range)
#
#         # Padrões de intervalos numéricos válidos:
#         pattern_range = r'^\d+\s*(-|\baté\b)\s*\d+$'  # "10-20", "100 até 200", "50 - 100"
#         pattern_open_range = r'^\b(até)\s+\d+$'  # "até 300"
#         pattern_plus = r'^\d+\s*\+$'  # "5+"
#         float_pattern = r'^-?\d+([.,])\d+$'  # Float simples, ex: "12.3" ou "8,9"
#
#         try:
#             has_int_number = int(text)  # Se for um número inteiro válido, não gera erro
#             has_int_number = True
#         except ValueError:
#             has_int_number = False  # Se der erro ao converter para int, não é número inteiro
#
#         has_float_number = bool(re.search(float_pattern, text))
#         has_pattern_range = bool(re.search(pattern_range, text, re.IGNORECASE))
#         has_pattern_open_range = bool(re.search(pattern_open_range, text, re.IGNORECASE))
#         has_pattern_plus = bool(re.search(pattern_plus, text, re.IGNORECASE))
#
#         # Se tem separador de números, sinal de "+" ou "até" - é um range
#         is_range = has_pattern_range or has_pattern_open_range or has_pattern_plus
#
#         # Se tem números inteiros ou float
#         is_number = has_int_number or has_float_number
#
#         return is_number, is_range
#
#     # Contadores
#     total_count = len([item for item in val if item is not None])  # Ignora valores None
#     number_count = 0
#     range_count = 0
#
#     # Dicionário para armazenar os resultados
#     detected_values = {}
#
#     for item in val:
#         if item is None:
#             continue  # Pula valores vazios
#
#         is_number, is_range = is_num_range(str(item))
#
#         # Contagem de números e ranges
#         if is_number:
#             number_count += 1
#         if is_range:
#             range_count += 1
#
#         detected_values[item] = (is_number, is_range)
#
#     # Calcula proporções
#     if total_count > 0:
#         range_ratio = range_count / total_count
#         number_ratio = number_count / total_count
#
#         if range_ratio >= threshold or (range_ratio + number_ratio >= (threshold * 1.1)):
#             print("\n🚀 Lista contém predominantemente ranges numéricos!\n")
#
#     return detected_values
#
# # Exemplo de lista de entrada
# valores = ["9-4", "8-12", "123", "456", "333", "101", "6-9", "7-8", "320", "123",
#            "23", "67", "23", "8-8", "8-4", "206", "187,1", "168,2", "149,3", "8-7",
#            "8-6", "-83,8", "-148,8", "-213,8", "-278,8", "-343,8", "7-12", "7-8",
#            "130,4", "111,5", "92,6", "73,7"]
#
# # Chamando a função
# resultado = detect_num_range(valores)
#
# # Exibindo os resultados
# for item, (is_number, is_range) in resultado.items():
#     print(f"'{item}': Número? {is_number} | Range? {is_range}")
























# from main_all import dd_list_columns, analyze_table, match_columns
# import re
# import pandas as pd
#
# def format_range(value):
#     if not isinstance(value, str) or len(value) < 2:
#         return None, None  # Retorna valores nulos se o dado for inválido
#
#     # Remover símbolos de moeda, espaços e caracteres não numéricos (exceto "-" e "+")
#     clean_value = re.sub(r'[^\d\-,+]', '', value)
#
#     # Se o formato for "Até R$360.000"
#     if "Até" in value or clean_value.startswith('-'):
#         min_value = 0  # Define o mínimo como 0
#         max_value = re.sub(r'\D', '', clean_value)  # Mantém apenas números no máximo
#         max_value = int(max_value)
#         return int(min_value), max_value if max_value else None
#
#     # Se for um range no formato "R$360.000 - R$4.800.000"
#     elif '-' in clean_value:
#         min_value, max_value = clean_value.split('-')
#         min_value = re.sub(r'\D', '', min_value)
#         max_value = re.sub(r'\D', '', max_value)
#         min_value = int(min_value) if min_value else None
#         max_value = int(max_value) if max_value else None
#         return min_value, max_value
#
#     # Se for um valor aberto como "R$10.000.000.000 +"
#     elif "+" in clean_value:
#         min_value = re.sub(r'\D', '', clean_value)
#         min_value = int(min_value) if min_value else None
#         max_value = 999999999999999  # Define o máximo fixo como 999999999999999
#         return min_value, max_value
#
#     return None, None  # Caso não caia em nenhum formato esperado
#
#
# def transform_value(new_data, matched_columns, unique_values, ref_list, ref_types):
#     # Filtrar os itens que possuem "Valor (range)" na coluna "Tipo"
#     print(f"Matched columns: {matched_columns}. \nmatched_columns:: {type(matched_columns)}")
#     print(f"Unique values: {unique_values}. \nunique_values: {type(unique_values)}")
#     print(f"Ref list: {ref_list}. \nref_list: {type(ref_list)}")
#     print(f"Ref types: {ref_types}. \nref_types: {type(ref_types)}")
#
#     print("Transformando valores tipo range")
#     range_columns = ref_types[ref_types['Tipo'] == 'Valor (range)']['Coluna']
#     print(f"Colunas: {range_columns}")
#
#     result_df = pd.DataFrame()
#
#     for column in range_columns:
#         if column in ref_list:
#             print(f"Coluna {column} presente na lista de colunas")
#             # Buscar os valores associados em unique_values
#             if column in unique_values:
#                 print(f"Coluna {column} presente no dicionario de valores únicos")
#                 unique_df = pd.DataFrame(unique_values[column], columns=[column])
#
#                 # Criar colunas de mínimo e máximo
#                 unique_df[[f"{column} - Min", f"{column} - Max"]] = unique_df[column].apply(lambda x: format_range(x)).apply(pd.Series)
#                 print(f"DF com os valores transformados: \n{unique_df}")
#
#                 # Armazenar o resultado
#                 result_df = pd.concat([result_df, unique_df], axis=0)
#                 print(f"DF resultante: \n{result_df}")
#
#             # Verificar se há correspondência no dicionário matched_columns
#             if column in matched_columns:
#                 print(f"Coluna {column} presente no dicionario de matches")
#                 mapped_column = matched_columns[column]
#
#                 if mapped_column in new_data:
#                     print(f"Coluna {mapped_column} presente no df novo")
#                     # Criar uma nova coluna com os valores transformados
#                     new_data[mapped_column] = pd.to_numeric(new_data[mapped_column], errors='coerce')
#
#                     def map_value(x):
#                         if pd.notnull(x):  # Evita erros com valores nulos
#                             row = result_df[
#                                 (result_df[f"{column} - Min"] <= x) &
#                                 (result_df[f"{column} - Max"] >= x)
#                                 ]
#                             return row[column].values[0] if not row.empty else None
#                         return None
#
#                     new_data[mapped_column] = new_data[mapped_column].apply(map_value)
#                     print(f"✔️ Transformação aplicada para {mapped_column}")
#
#     return new_data
#
# def main():
#     pd.set_option('display.max_rows', None)
#     pd.set_option('display.max_columns', None)
#     pd.set_option('display.width', None)
#     pd.set_option('display.expand_frame_repr', False)
#
#     ref_path = "ref_data_empresa.csv"
#     new_path = "new_data_empresa.csv"
#
#     print("Carregando arquivos CSV...")
#     # Carrega os dados mantendo o formato original das colunas (todas como texto)
#     ref_data = pd.read_csv(ref_path, dtype=str).dropna(how='all')
#     new_data = pd.read_csv(new_path, dtype=str).dropna(how='all')
#
#     print("Avaliando listas suspensas na tabela de referência")
#     ref_data, ref_dd_list = dd_list_columns(ref_data)
#     print(f"Lista de colunas drop down: \n{ref_dd_list}")
#
#     print("\n📊 Analisando tipos de dados...")
#     # 🔹 Executa a função apenas uma vez e armazena os retornos
#     df_ref, ref_types, unique_values_dict_ref = analyze_table(ref_data, ref_path)
#     df_new, new_types, _ = analyze_table(new_data, new_path)
#
#     matched_columns = match_columns(df_ref, df_new, ref_types, new_types, ref_path, new_path)
#     new_data = transform_value(df_new, matched_columns, unique_values_dict_ref, ref_dd_list, ref_types)
#
#     # Substituir todas as ocorrências da string "NaN" por valores vazios (sem inplace=True)
#     new_data.replace("nan", "", inplace=True)
#
#     print(f"DF final:\n{new_data}")
#
# if __name__ == "__main__":
#     main()
