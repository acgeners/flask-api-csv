from code_sup import VALID_DDD, meses # lista_suspensa_columns
import pandas as pd
import re
from difflib import SequenceMatcher

#---------------------------AVALIAR COLUNAS E IDENTIFICAR TIPO---------------------------#
def colum_names_check(df, filename):
    cols = pd.Series(df.columns)
    # Para cada coluna duplicada, iteramos e renomeamos com um índice
    for dup in cols[cols.duplicated()].unique():
        dup_idx = cols[cols == dup].index.tolist()
        print(f"Coluna duplicada em {filename}: {dup_idx}")
        for i, idx in enumerate(dup_idx, start=1):
            cols[idx] = f"{dup}_{i}"
            print(f"Coluna renomeada em {filename}: de '{dup}' para '{cols[idx]}' no índice {idx}")
    df.columns = cols
    return df

def detect_and_format_dates(df, detected_types):
    """Detecta colunas de data e converte para o formato dd/mm/aaaa."""
    print("🔍 Detectando e formatando colunas de data...")

    date_pattern = re.compile(r'^\s*(\d{1,2})[-/.\s](\d{1,2})[-/.\s](\d{2,4})\s*$')

    def infer_date_format(series):
        """Determina o formato da data e retorna a string formatada (dd/mm/aaaa)."""
        extracted = series.str.extract(date_pattern)

        if extracted.isnull().all().all():
            return None

        first_numbers = extracted[0].dropna().astype("Int64")
        middle_numbers = extracted[1].dropna().astype("Int64")
        last_numbers = extracted[2].dropna().astype(str)
        print(f"\nPrimeiros números: \n{first_numbers}, \npróximos: \n{middle_numbers}, \nfinal: \n{last_numbers}")

        # Caso o primeiro número seja maior que 12, provavelmente é o dia
        if (first_numbers > 12).sum() > 0:
            date_str = first_numbers.astype(str) + "/" + middle_numbers.astype(str) + "/" + last_numbers
            print(f"\nDate str do first > 12: \n{date_str}")
        # Se o segundo número for maior que 12, ele deve ser o dia (portanto, inverte)
        elif (middle_numbers > 12).sum() > 0:
            date_str = middle_numbers.astype(str) + "/" + first_numbers.astype(str) + "/" + last_numbers
            print(f"\nDate str do middle > 12: \n{date_str}")
        else:
            date_str = first_numbers.astype(str) + "/" + middle_numbers.astype(str) + "/" + last_numbers
            print(f"\nDate str do first == middle: \n{date_str}")

        # Verifica se a conversão para datetime funciona para algum valor
        date_series = pd.to_datetime(date_str, format="%d/%m/%Y", errors="coerce")
        return date_str if date_series.notna().any() else None

    def format_date(date):
        """Converte datas escritas em texto para dd/mm/yyyy."""
        try:
            parsed_date = pd.to_datetime(date, errors="coerce")
            return parsed_date.strftime('%d/%m/%Y') if not pd.isna(parsed_date) else date
        except Exception:
            return date

    for col in df.columns:
        # Verifica se o nome da coluna sugere que ela contenha datas
        if any(keyword in col.lower() for keyword in ['data', 'atualizado', 'atualização']):
            print(f"\nColuna {col} contém as palavras 'data', 'atualização' ou 'atualizado'")
            sample_values = df[col].dropna().astype(str).sample(min(len(df[col]), 20), random_state=42)
            print(f"\nSample values é data: \n{sample_values}")

            # Verifica se a coluna contém apenas valores no formato de data
            if sample_values.str.fullmatch(date_pattern, na=False).any():
                print(f"\nSample values no formato padrão: \n{sample_values}")
                date_format = infer_date_format(df[col])
                if date_format is not None:
                    # Converte a série de string para datetime e depois a volta para string com o formato dd/mm/aaaa
                    date_dt = pd.to_datetime(date_format, format="%d/%m/%Y", errors="coerce")
                    if hasattr(date_dt, 'dt'):  # Se for uma Series
                        df[col] = date_dt.dt.strftime("%d/%m/%Y")
                    else:  # Se for um Timestamp
                        df[col] = date_dt.strftime("%d/%m/%Y") if date_dt is not pd.NaT else date_format
                    detected_types[col] = "Data"
                    print(f"\n🗓️ Coluna '{col}' identificada como Data e formatada.")
                    print(f"\nColuna final (patern) {col}: \n{df[col]}")
                else:
                    print(f"⚠️ Falha na conversão para data na coluna '{col}'")

            # Verifica se há datas escritas em formato de texto (ex: "20 de março de 2023")
            elif sample_values.str.contains('|'.join(meses), case=False, regex=True, na=False).any():
                print(f"\nSample values contém nomes de meses: {sample_values}")
                df[col] = df[col].apply(lambda x: format_date(x) if pd.notna(x) else x)
                detected_types[col] = "Data"
                print(f"\n🗓️ Coluna '{col}' identificada como Data e formatada.")
                print(f"\nColuna final (nome mês) {col}: \n{df[col]}")

    return df

def detect_account(df, detected_types):
    """Detecta colunas de e-mail, LinkedIn e Instagram, garantindo que a validação seja precisa."""

    print("\n🔍 Detectando colunas de e-mail, LinkedIn e Instagram...")

    # Expressões regulares para identificação
    email_pattern = re.compile(r"^[\wÀ-ÖØ-öø-ÿ._%+-]+@[a-zA-Z0-9.-]+\.com(?:\.br)?$")
    linkedin_pattern = re.compile(r"^https?://(www\.)?linkedin\.com/in/[\w\-]+$")
    instagram_pattern = re.compile(r"^@[\w.]+$")

    for col in df.columns:
        if col not in detected_types and df[col].dtype == 'object':
            values = df[col].dropna().astype(str).str.strip()  # Remove espaços invisíveis

            # Criar uma série de booleanos para verificar quais valores passam na regex
            email_matches = values.str.match(email_pattern)
            linkedin_matches = values.str.match(linkedin_pattern)
            instagram_matches = values.str.match(instagram_pattern)

            # Aplicar a classificação
            if email_matches.all():
                detected_types[col] = "E-mail"
            elif linkedin_matches.all():
                detected_types[col] = "Linkedin"
            elif instagram_matches.all():
                detected_types[col] = "Instagram"

    # Exibir o resultado final
    for col, col_type in detected_types.items():
        print(f"📧 Coluna '{col}' identificada como {col_type}.")

    return detected_types

def normalize_phone(value):
    if isinstance(value, str):
        if len(value) == 11:
            return f'+55 ({value[:2]}) {value[2:7]}-{value[7:]}'
        elif len(value) == 10:
            return f'+55 ({value[:2]}) {value[2:6]}-{value[6:]}'
        elif len(value) == 12:
            return f'+{value[:2]} ({value[2:4]}) {value[4:8]}-{value[8:]}'
        elif len(value) == 13:
            return f'+{value[:2]} ({value[2:4]}) {value[4:9]}-{value[9:]}'

        else:
            print("Falha ao formatar telefone - número de caracteres não bate")
            return None
    else:
        print("Falha ao formatar telefone - falha ao identificar dado")
        return None

def normalize_cpf(value):
    if isinstance(value, str):
        if len(value) == 11:
            return f'{value[:3]}.{value[3:6]}.{value[6:9]}-{value[9:]}'
        else:
            print(f"Não foi possível formatar o cpf - não tem 11 caracteres")
            return None
    else:
        print("Não foi possível formatar o cpf - falha ao identificar dado")
        return None

def normalize_dataframe(df, detected_types):
    """Remove caracteres não alfanuméricos de todas as colunas não identificadas anteriormente."""
    print("🔍 Normalizando colunas - removendo caracteres especiais...")

    def clean_column(value):
        if isinstance(value, str):
            # Remove caracteres que não são letras, números ou espaços
            return re.sub(r'\D', '', str(value))
        return value

    # Criar uma cópia do DataFrame para evitar modificar o original
    df_normalized = df.copy()

    normalize_columns = [
        col for col in df_normalized.select_dtypes(include=["object"]).columns
        if detected_types.get(col, "") in ("Telefone", "CPF")  # Retorna "" se col não existir
    ]

    # Aplicar a normalização apenas nessas colunas
    for col in normalize_columns:
        # Primeiro, aplica uma limpeza nos textos
        df_normalized[col] = df_normalized[col].map(clean_column)
        # Em seguida, formata de acordo com o tipo detectado
        if detected_types.get(col, "") == "Telefone":
            df_normalized[col] = df_normalized[col].map(normalize_phone)
        elif detected_types.get(col, "") == "CPF":
            df_normalized[col] = df_normalized[col].map(normalize_cpf)

    print(f"✅ Colunas normalizadas: {normalize_columns}")

    return df_normalized

def is_valid_cpf(value):
    """Verifica se um valor é um CPF válido seguindo o algoritmo da Receita Federal."""
    digits = re.sub(r'\D', '', str(value))

    if len(digits) != 11 or digits == digits[0] * 11:
        return None

    sum1 = sum(int(digits[i]) * (10 - i) for i in range(9))
    digit1 = (sum1 * 10) % 11
    digit1 = 0 if digit1 >= 10 else digit1

    sum2 = sum(int(digits[i]) * (11 - i) for i in range(10))
    digit2 = (sum2 * 10) % 11
    digit2 = 0 if digit2 >= 10 else digit2

    return "CPF" if digits[-2:] == f"{digit1}{digit2}" else None

def is_phone_number(value):
    """Verifica se um valor é um número de telefone válido considerando apenas o DDI do Brasil (55)."""
    digits = re.sub(r'\D', '', str(value))

    if len(digits) in [10, 11]:
        ddd, phone_number = digits[:2], digits[2:]
        if ddd in VALID_DDD and ((len(digits) == 10 and re.match(r'^[2-5]\d{7}$', phone_number)) or
                                 (len(digits) == 11 and re.match(r'^9\d{8}$', phone_number))):
            return "Telefone"
    elif len(digits) in [12, 13]:
        ddi, ddd, phone_number = digits[:2], digits[2:4], digits[4:]
        if ddi == "55" and ddd in VALID_DDD:
            if len(digits) == 12 and re.match(r'^[2-5]\d{7}$', phone_number):
                return "Telefone"
            elif len(digits) == 13 and re.match(r'^9\d{8}$', phone_number):
                return "Telefone"

    return None

def detect_phone_and_cpf(df, detected_types):
    """Verifica se as colunas são Telefones ou CPF usando as funções corretas."""
    for col in df.columns:
        if col not in detected_types and df[col].dtype == 'object':
            values = df[col].dropna().astype(str)

            # Primeiro, verifica CPF corretamente
            cpf_check = values.apply(is_valid_cpf)
            if cpf_check.dropna().any():  # Corrigido para considerar apenas valores válidos
                detected_types[col] = "CPF"
                continue  # Se já foi detectado como CPF, não precisa testar telefone

            # Agora, verifica Telefone corretamente
            phone_check = values.apply(is_phone_number)
            if phone_check.dropna().any():  # Corrigido para considerar apenas valores válidos
                detected_types[col] = "Telefone"

    return detected_types

def detect_column_type(df, detected_types):
    """Define tipos de coluna restantes como 'Número', 'Número com erro' ou 'Texto'.
       Para colunas de texto, retorna uma lista de valores únicos conforme a proporção especificada."""

    print("🔍 Detectando colunas restantes como número ou texto...")

    unique_values_dict = {}

    for col in df.columns:
        if col not in detected_types:
            # Converte para numérico, mantendo NaN para não numéricos
            numeric_values = pd.to_numeric(df[col], errors='coerce')
            numeric_ratio = numeric_values.notna().mean()  # Proporção de valores numéricos na coluna

            if pd.to_numeric(df[col], errors='coerce').notna().all():
                detected_types[col] = "Número"
            elif numeric_ratio >= 0.95:
                detected_types[col] = "Número com erro"
            else:
                detected_types[col] = "Texto"

        # Análise adicional para colunas de texto
        if detected_types[col] == "Texto":
            unique_values = df[col].dropna().unique()  # Obtém valores únicos, excluindo NaN

            unique_values_dict[col] = unique_values.tolist()

    for col, col_type in detected_types.items():
        print(f"📊 Coluna '{col}' identificada como {col_type}.")

    return detected_types, unique_values_dict

def correct_number(df, detected_types):
    for col in df.columns:
        if detected_types.get(col) == "Número com erro":
            print(f"🔧 Corrigindo coluna '{col}'...")

            # Remove todos os caracteres não numéricos
            df[col] = df[col].astype(str).apply(lambda x: re.sub(r'\D', '', x))

            # Converte a coluna para tipo numérico, substituindo strings vazias por NaN
            df[col] = pd.to_numeric(df[col], errors='coerce')

            # Atualiza o tipo detectado para 'Número'
            detected_types[col] = "Número"

            print(f"✅ Coluna '{col}' corrigida e atualizada para o tipo 'Número'.")

    return df, detected_types

def analyze_table(df, filename):
    """Executa todas as etapas na sequência correta."""
    print(f"\nAnalisando dados em: {filename}")

    # Configura pandas para exibir todas as colunas na saída
    pd.set_option('display.max_columns', None)  # Exibe todas as colunas
    pd.set_option('display.width', 200)  # Ajusta a largura do terminal para evitar truncamento

    detected_types = {}

    df = colum_names_check(df, filename)

    df = detect_and_format_dates(df, detected_types)
    detected_types = detect_account(df, detected_types)

    detected_types = detect_phone_and_cpf(df, detected_types)
    df = normalize_dataframe(df, detected_types)

    # Detecta tipos de colunas e obtém valores únicos para colunas de texto
    detected_types, unique_values_dict = detect_column_type(df, detected_types)
    #
    # Corrige colunas classificadas como 'Número com erro'
    df, detected_types = correct_number(df, detected_types)

    result_df = pd.DataFrame(list(detected_types.items()), columns=['Coluna', 'Tipo'])
    # print(f"DF final: {df.head(5).to_string(index=False)}")
    # # for col in df.columns:
    # #     print(f"Coluna '{col}': {type(col)}")
    # # print(f"Lista: {unique_values_dict}")

    return df, result_df, unique_values_dict

#---------------------------FAZER O MATCH DAS COLUNAS---------------------------#
def extract_year(value):
    """Extrai os últimos 4 números da string como ano, se possível."""
    match = re.search(r'(\d{4})$', str(value))  # Procura um conjunto de 4 números no final
    return int(match.group(1)) if match else None  # Converte para inteiro ou retorna None

def date_var(normalized_new, min_valid_percent=0.8):
    """
        Processa uma Series de datas normalizadas (contendo apenas dígitos no formato DDMMYYYY)
        e retorna a variação (em dias) entre datas consecutivas.

        Parâmetros:
          normalized_new: Series com valores de datas contendo apenas dígitos.
          min_valid_percent: Percentual mínimo de dados válidos para continuar a operação.
        """

    # 🔹 1. Imprimir os dados originais
    print(f"\n📌 Dados originais:\n{normalized_new}\n")

    # 🔹 2. Remover valores nulos e converter para string
    valid_dates = normalized_new.dropna().astype(str)

    # 🔹 3. Filtrar apenas os valores que têm exatamente 8 caracteres (DDMMYYYY)
    valid_dates_filtered = valid_dates[valid_dates.str.len() == 8]

    # 🔹 4. Verificar a porcentagem de dados válidos
    valid_percent = len(valid_dates_filtered) / len(valid_dates) if len(valid_dates) > 0 else 0

    if valid_percent < min_valid_percent:
        print(f"⚠️ Apenas {valid_percent:.0%} dos dados estão no formato correto. Abortando operação.")
        return pd.Series(dtype="int64")  # Retorna uma Series vazia

    print(f"✅ {valid_percent:.0%} dos dados estão corretos ({len(valid_dates_filtered)} valores). Continuando...\n")

    # 🔹 5. Formatar as datas como DD/MM/YYYY
    valid_dates_filtered = valid_dates_filtered.apply(lambda x: f"{x[:2]}/{x[2:4]}/{x[4:]}")
    print(f"📆 Datas formatadas: \n{valid_dates_filtered}\n")

    # 🔹 6. Converter para datetime
    valid_dates_filtered = pd.to_datetime(valid_dates_filtered, format="%d/%m/%Y", errors="coerce").dropna()
    print(f"📅 Datas convertidas para datetime: \n{valid_dates_filtered}\n")

    # 🔹 7. Garantir que seja uma Series e ordenar
    valid_dates_filtered = pd.Series(valid_dates_filtered).sort_values(ignore_index=True)
    print(f"📌 Datas ordenadas: \n{valid_dates_filtered}\n")

    # 🔹 8. Calcular a variação entre valores consecutivos (em dias)
    date_variation = valid_dates_filtered.diff().dt.days
    print(f"📊 Variação entre datas (dias): \n{date_variation}\n")

    return date_variation


def year_evaluation(dates):
    # Extrair os anos da coluna
    data_years = dates.dropna().astype(str).apply(extract_year).dropna()

    # Garantir que as colunas contenham valores inteiros antes de continuar
    if data_years.dtype != 'int64':
        return 0  # Retorna similaridade zero se não for possível calcular

    # Calcular média e mediana dos anos extraídos
    data_mean = int(data_years.mean()) if not data_years.empty else 0
    # data_median = int(data_years.median()) if not data_years.empty else 0

    return data_mean

def match_columns(ref_data, new_data, ref_types, new_types, filename1, filename2, threshold=0.59):
    matched_columns = {}
    match = {}
    not_match_new = set(new_data.columns)
    not_match_ref = set(ref_data.columns)
    print("\nIniciando correspondência de colunas...")

    for ref_col in ref_data.columns:
        best_match = None
        best_score = 0
        best_new_col = None  # Armazena a melhor coluna correspondente da tabela 2

        for new_col in new_data.columns:
            # Verifica se os tipos de dados são compatíveis
            ref_col_type = ref_types.loc[ref_types['Coluna'] == ref_col, 'Tipo'].values[0] if ref_col in ref_types[
                'Coluna'].values else 'Desconhecido'
            new_col_type = new_types.loc[new_types['Coluna'] == new_col, 'Tipo'].values[0] if new_col in new_types[
                'Coluna'].values else 'Desconhecido'

            if ref_col_type == new_col_type:  # Apenas compara colunas do mesmo tipo
                # print(f"Comparando {new_col} ({new_col_type}) com {ref_col} ({ref_col_type})")
                cleaned_new_col = re.sub(r'[.\-]', '', new_col).lower()
                cleaned_ref_col = re.sub(r'[.\-]', '', ref_col).lower()
                name_similarity = SequenceMatcher(None, cleaned_new_col, cleaned_ref_col).ratio()

                if name_similarity == 1: #TODO deixa isso?
                    matched_columns[new_col] = ref_col
                    match.update({new_col: ref_col})
                    not_match_new.discard(new_col)
                    not_match_ref.discard(ref_col)
                    print(f"✅ Coluna '{new_col}' foi renomeada para '{ref_col}' por similaridade de nome {name_similarity:.2f}")
                    break  # Se a similaridade for alta o suficiente, já garantimos o match
                else:
                    if ref_col_type == "Data":
                        date_cleaned_new_col = re.sub(r'\b(?:data|de|em|da)\b',
                                                      '', re.sub(r'[.\-]', '', new_col), flags=re.IGNORECASE).lower()

                        date_cleaned_ref_col = re.sub(r'\b(?:data|de|em|da)\b',
                                                      '', re.sub(r'[.\-]', '', ref_col), flags=re.IGNORECASE).lower()
                        name_similarity = SequenceMatcher(None, date_cleaned_new_col, date_cleaned_ref_col).ratio()
                        if new_col == 'Atualizado em' or ref_col == 'Data da Última Atualização':
                            print(f"{date_cleaned_new_col} x {date_cleaned_ref_col}: name similarity = {name_similarity:.2f}")

                data_similarity = 0
                if new_data.get(new_col) is not None and ref_data.get(ref_col) is not None:
                    if ref_col_type == "Texto":
                        common_values = set(new_data[new_col].dropna().astype(str)) & set(ref_data[ref_col].dropna().astype(str))
                        total_values = set(new_data[new_col].dropna().astype(str)) | set(ref_data[ref_col].dropna().astype(str))

                        if total_values:
                            data_similarity = len(common_values) / len(total_values)
                            print(f"TEXTO - Similaridade {new_col} e {ref_col}: {data_similarity}")

                    elif ref_col_type == "Data":
                        normalized_new = new_data[new_col].str.replace(r'\D', '', regex=True)
                        normalized_ref = ref_data[ref_col].str.replace(r'\D', '', regex=True)

                        year_new = year_evaluation(new_data[new_col])
                        year_ref = year_evaluation(ref_data[ref_col])
                        print(f"Ano new_data: {year_new}, Ano ref: {year_ref}")

                        # Média das diferenças normalizada pelo ano atual
                        data_age = (100 - (abs(year_new - year_ref))) / 100
                        print(f"Coeficiente ano: {data_age}")

                        variation_new = date_var(normalized_new)
                        variation_ref = date_var(normalized_ref)

                        if isinstance(variation_new, pd.Series):
                            variation_new = variation_new.mean()
                        if isinstance(variation_ref, pd.Series):
                            variation_ref = variation_ref.mean()

                        scaling_factor = 0.3  # ajusta esse valor conforme necessário
                        variation_diff = abs(variation_new - variation_ref)

                        # Normaliza entre 0 e 1
                        variation_score = 1 - ((variation_diff * scaling_factor) / max(variation_new, variation_ref, 1))
                        print(f"Variação new: {variation_new}, Variação ref: {variation_ref}, Variação total: {variation_score}")
                        # Combinar idade e variação para calcular similaridade final
                        data_similarity = (data_age * 0.5) + (variation_score * 0.5)
                        if new_col == 'Atualizado em' or ref_col == 'Data da Última Atualização':
                            print(f"{new_col} x {ref_col}: data similarity = {data_similarity:.2f}")

                    else:  #TODO add regra?
                        # data_similarity = 1
                        new_mode = new_data[new_col].dropna().mode().values
                        ref_mode = ref_data[ref_col].dropna().mode().values

                        common_values = set(new_mode) & set(ref_mode)
                        total_values = set(new_mode) | set(ref_mode)

                        if total_values:
                            data_similarity = len(common_values) / len(total_values)
                            print(f"NOT Texto/Data - Similaridade {new_col} e {ref_col}: {data_similarity}")

                    overall_score = (name_similarity * 0.5) + (data_similarity * 0.5)
                    if new_col == 'Atualizado em' or ref_col == 'Data da Última Atualização':
                        print(f"{new_col} x {ref_col}: score = {overall_score:.2f}")

                    # if new_col == 'Atualizado em' or ref_col == 'Data da Última Atualização':
                    #     print(f"{new_col} x {ref_col}: {overall_score:.2f}")

                    # print(f"Comparando '{new_col}' com '{ref_col}':\n"
                    #       f"  - Similaridade de nome: {name_similarity:.2f}\n"
                    #       f"  - Similaridade de dados: {data_similarity:.2f}\n"
                    #       f"  - Score final: {overall_score:.2f}")

                    if overall_score > best_score:
                        best_score = overall_score
                        best_match = ref_col
                        best_new_col = new_col  # Armazena a coluna correspondente

        if best_match and best_score >= threshold:
            # if best_match in matched_columns: # TODO regra pra considerar só a comparação com maior valor
            #     print(f"Comparando: {matched_columns[best_match]} com {best_match}")
            #     if best_match > matched_columns[best_match]:
            #         matched_columns[best_new_col] = best_score
            #         print(f"✅ Valor da coluna '{best_new_col}' foi alterado para {best_score:.2f}")

            # else:     # TODO conferir a ordem aqui, que ta errada
            matched_columns[best_new_col] = best_match
            not_match_new.discard(best_new_col)
            not_match_ref.discard(best_match)
            match.update({best_new_col: best_match})
            print(f"✅ Coluna '{best_new_col}' foi renomeada para '{best_match}' com score {best_score:.2f}")

    print("Correspondência de colunas concluída!\n\nMatchs realizados:")
    for chave, valor in match.items():
        print(f"{chave}: {valor}")
    print(f"Colunas sem correspondência em {filename1}: {not_match_ref}\n")
    print(f"Colunas sem correspondência em {filename2}: {not_match_new}")

    return matched_columns

#---------------------------TRANSFORMAR OS DADOS DA TABELA NOVA---------------------------#
def transform_data(ref_data, new_data, matched_columns):
    print("Iniciando transformação da coluna...")

    # 1. Renomeia as colunas de new_data com base no dicionário:
    transformed_data = new_data.rename(columns=matched_columns)
    print(f"Transformed data (renomear): {transformed_data}")

    # 2. Remover colunas extras em `transformed_data` que não existem em `ref_data`
    transformed_data = transformed_data[[col for col in ref_data.columns if col in transformed_data.columns]].copy()
    print(f"Transformed data (remover): {transformed_data}")

    # 3. Adicionar colunas ausentes em `transformed_data`, preenchendo com "" (ou `None`, se preferir)
    missing_cols = set(ref_data.columns) - set(transformed_data.columns)
    for col in missing_cols:
        transformed_data.loc[:, col] = ""  # ⚠️ Agora usamos .loc para evitar o warning

    print(f"Transformed data (add): {transformed_data}")

    # 4. Garantir que a ordem das colunas seja a mesma do `ref_data`
    transformed_data = transformed_data.reindex(columns=ref_data.columns, fill_value="")

    print("Transformação de dados concluída!\n")
    print(f"Transformed data (ordenar): {transformed_data}")
    return transformed_data

#---------------------------EXECUTAR PROCESSO COMPLETO---------------------------#
def main():
    ref_path = "ref_data.csv"  # Altere para o caminho correto no Bubble
    new_path = "new_data.csv"  # Altere para o caminho correto no Bubble
    output_path = "refined_data.csv"

    print("Carregando arquivos CSV...")
    ref_data = pd.read_csv(ref_path)
    new_data = pd.read_csv(new_path)

    print("📊 Analisando tipos de dados...")
    # 🔹 Executa a função apenas uma vez e armazena os retornos
    df_ref, ref_types, unique_values_dict_ref = analyze_table(ref_data, ref_path)
    df_new, new_types, unique_values_dict_new = analyze_table(new_data, new_path)

    matched_columns = match_columns(df_ref, df_new, ref_types, new_types, ref_path, new_path)
    transformed_data = transform_data(df_ref, df_new, matched_columns)

    transformed_data.to_csv(output_path, index=False)
    print(f"✅ Dados transformados salvos como: {output_path}")
    print(matched_columns)

if __name__ == "__main__":
    main()
