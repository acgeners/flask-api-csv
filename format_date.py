import pandas as pd
from dateutil import parser
import re

def detect_date_format(date_series):
    """
    Analisa uma coluna de datas para determinar se o formato mais comum é DD/MM/YYYY ou MM/DD/YYYY.
    Retorna 'dayfirst' como True se for DD/MM/YYYY, False se for MM/DD/YYYY.
    """
    dd_count = 0
    mm_count = 0

    for date in date_series.dropna():
        match = re.match(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})", str(date))
        if match:
            first, second, _ = map(int, match.groups())
            if first > 12:
                dd_count += 1  # O primeiro número só pode ser um dia
            elif second > 12:
                mm_count += 1  # O segundo número só pode ser um mês

    # Se houver mais ocorrências de primeiro número > 12, é DD/MM/YYYY
    if dd_count > mm_count:
        return True  # dayfirst=True
    elif mm_count > dd_count:
        return False  # dayfirst=False
    else:
        return True  # Por padrão, assume DD/MM/YYYY

def is_date(value, dayfirst=True):
    """Tenta converter um valor para datetime, retornando True se for possível."""
    try:
        _ = parser.parse(value, dayfirst=dayfirst)
        return True
    except (ValueError, TypeError):
        return False

def convert_to_standard_date(value, dayfirst=True):
    """Converte qualquer formato de data para o formato dd/mm/aaaa garantindo a interpretação correta."""
    try:
        parsed_date = parser.parse(value, dayfirst=dayfirst)
        return parsed_date.strftime('%d/%m/%Y')
    except (ValueError, TypeError):
        return value


def main():
    ref_path = "date.csv"  # Altere para o caminho correto no Bubble

    print("Carregando arquivos CSV...")
    df = pd.read_csv(ref_path)

    pd.set_option('display.max_columns', None)  # Exibe todas as colunas
    pd.set_option('display.width', 200)  # Ajusta a largura do terminal para evitar truncamento

    print("📊 Analisando tipos de dados...")
    for col in df.columns:
        if df[col].astype(str).apply(lambda x: is_date(x, dayfirst=True)).mean() > 0.9:
            dayfirst_setting = detect_date_format(df[col])  # Detecta o formato da coluna
            print(f"Coluna '{col}' identificada como data (dayfirst={dayfirst_setting}) e será convertida.")
            df[col] = df[col].astype(str).apply(lambda x: convert_to_standard_date(x, dayfirst=dayfirst_setting))

    print(f"DF final: \n{df}")

if __name__ == "__main__":
    main()





# import pandas as pd
# from dateutil import parser
#
# def is_date(value):
#     """Tenta converter um valor para datetime, retornando True se for possível."""
#     try:
#         _ = parser.parse(value, dayfirst=False)  # Tenta converter a data
#         return True
#     except (ValueError, TypeError):
#         return False
#
# def convert_to_standard_date(value):
#     """Converte qualquer formato de data para o formato dd/mm/aaaa"""
#     try:
#         parsed_date = parser.parse(value, dayfirst=False)  # Converte a data
#         return parsed_date.strftime('%d/%m/%Y')  # Retorna no formato dd/mm/aaaa
#     except (ValueError, TypeError):
#         return value  # Retorna o original se não for uma data

# Recarregando as bibliotecas necessárias após resetar o estado






# import pandas as pd
# import re
#
# def detect_and_format_dates(new_data):
#     print("🔍 Iniciando detecção de colunas de data na tabela...")
#
#     meses = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
#              "novembro", "dezembro", "january", "february", "march", "april", "may", "june", "july", "august",
#              "september", "october", "november", "december"]
#
#     # Regex com âncoras para garantir que a string inteira seja a data
#     date_pattern = re.compile(r'^\s*(\d{1,2})[-/.\s](\d{1,2})[-/.\s](\d{2,4})\s*$')
#
#     def infer_date_format(date_series):
#         """Determina o formato das datas e as converte corretamente para datetime."""
#         print("🔍 Inferindo formato para coluna...")
#         extracted = date_series.str.extract(date_pattern)
#         if extracted.isnull().all().all():
#             print("⚠️ Nenhuma correspondência encontrada pela regex.")
#             return None
#
#         first_numbers = extracted[0].dropna().astype(int, errors="ignore")
#         middle_numbers = extracted[1].dropna().astype(int, errors="ignore")
#         last_numbers = extracted[2].dropna().astype(str)
#
#         print(f"📊 Primeiros números detectados: {first_numbers.unique()}")
#         print(f"📊 Números do meio detectados: {middle_numbers.unique()}")
#         print(f"📊 Últimos números detectados (anos): {last_numbers.unique()}")
#
#         # Se o primeiro número for maior que 12, assumimos que é DD/MM/YYYY
#         if (first_numbers > 12).sum() > 0:
#             print("✅ Padrão identificado como DD/MM/YYYY")
#             date_str = first_numbers.astype(str) + "/" + middle_numbers.astype(str) + "/" + last_numbers
#             date_column = pd.to_datetime(date_str, format="%d/%m/%Y", errors="coerce")
#         # Se o segundo número (que seria o dia) for maior que 12, assumimos MM/DD/YYYY
#         elif (middle_numbers > 12).sum() > 0:
#             print("✅ Padrão identificado como MM/DD/YYYY")
#             date_str = middle_numbers.astype(str) + "/" + first_numbers.astype(str) + "/" + last_numbers
#             date_column = pd.to_datetime(date_str, format="%d/%m/%Y", errors="coerce")
#         else:
#             print("⚠️ Incapaz de inferir com precisão. Tentando ambas as opções...")
#             date_str = first_numbers.astype(str) + "/" + middle_numbers.astype(str) + "/" + last_numbers
#             date_column_1 = pd.to_datetime(date_str, dayfirst=False, errors="coerce")
#             date_column_2 = pd.to_datetime(date_str, dayfirst=True, errors="coerce")
#             if date_column_1.isna().sum() < date_column_2.isna().sum():
#                 date_column = date_column_1
#                 print("✅ Selecionado MM-DD-YYYY como formato correto.")
#             else:
#                 date_column = date_column_2
#                 print("✅ Selecionado DD-MM-YYYY como formato correto.")
#
#         if date_column.isna().all():
#             print("⚠️ A conversão resultou em todos NaN.")
#             return None
#         return date_column
#
#     def format_date(date):
#         """Converte datas escritas em inglês e outros formatos para dd/mm/yyyy."""
#         try:
#             parsed_date = pd.to_datetime(date, errors="coerce")
#             return parsed_date.strftime('%d/%m/%Y') if not pd.isna(parsed_date) else date
#         except Exception:
#             return date
#
#     for col in new_data.columns:
#         print(f"\n🔎 Analisando coluna: '{col}'")
#         column_modified = False
#
#         # Verifica se o nome da coluna contém palavras-chave
#         if any(keyword in col.lower() for keyword in ['data', 'atualizado']):
#             sample_values = new_data[col].dropna().astype(str).sample(min(len(new_data[col]), 20), random_state=42)
#             print(f"📋 Exemplo de valores na coluna '{col}': {sample_values.tolist()}")
#
#             # Usamos fullmatch para garantir que toda a string corresponda ao padrão
#             if sample_values.str.fullmatch(date_pattern, na=False).any():
#                 print(f"✅ A coluna '{col}' contém padrões de data.")
#                 date_format = infer_date_format(new_data[col])
#                 if date_format is not None and pd.api.types.is_datetime64_any_dtype(date_format):
#                     print(f"✅ Aplicando formatação na coluna '{col}'")
#                     new_data[col] = date_format.dt.strftime('%d/%m/%Y')
#                     column_modified = True
#                 else:
#                     print(f"⚠️ Falha na conversão para datetime na coluna '{col}'")
#             elif sample_values.str.contains('|'.join(meses), case=False, regex=True, na=False).any():
#                 print(f"✅ A coluna '{col}' contém meses escritos por extenso.")
#                 new_data[col] = new_data[col].apply(lambda x: format_date(x) if pd.notna(x) else x)
#                 column_modified = True
#
#         if column_modified:
#             print(f"🗓️ Coluna '{col}' detectada como data e formatada para dd/mm/aaaa")
#             print(new_data[col].head(10))
#
#     print("📅 Detecção e formatação de datas concluída!\n")
#     return new_data
#
# # Carregar o arquivo CSV
# file_path = "teste.csv"
# new_data = pd.read_csv(file_path)
#
# # Aplicar a função de detecção e formatação de datas
# new_data = detect_and_format_dates(new_data)
#
# # Exibir o resultado final
# print("\n📊 Resultado Final:")
# print(new_data.head(10))
