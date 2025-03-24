from code_sup import VALID_DDD, meses # lista_suspensa_columns
import pandas as pd
import re
from difflib import SequenceMatcher
from datetime import datetime as dt

#---------------------------AVALIAR COLUNAS E IDENTIFICAR TIPO---------------------------#
def detect_and_format_dates(df, detected_types):
    """Detecta colunas de data e converte para o formato dd/mm/aaaa."""
    print("🔍 Detectando e formatando colunas de data...")

    date_pattern = re.compile(r'^\s*(\d{1,2})[-/.\s](\d{1,2})[-/.\s](\d{2,4})\s*$')
    date_pattern2 = re.compile(r"(\d{2}-\d{2}-\d{4})")

    def infer_date_format(series): # TODO alguma coisa errada aqui, que o "Atualizado em" ta do contrario
        """Determina o formato da data e a converte corretamente para datetime."""
        extracted = series.str.extract(date_pattern)
        extracted2 = series.str.extract(date_pattern2)

        if extracted.isnull().all().all() and extracted2.isnull().all().all():
            return None

        first_numbers = extracted[0].dropna().astype("Int64")
        middle_numbers = extracted[1].dropna().astype("Int64")
        last_numbers = extracted[2].dropna().astype(str)

        # if sample_values.str.fullmatch(date_pattern2, na=False).any():
        #     date_str2 = (middle_numbers.astype(str).str.zfill(2) + "/" +
        #                  first_numbers.astype(str).str.zfill(2) + "/" +
        #                  last_numbers)
        #     date_column = pd.to_datetime(date_str2, format="%d/%m/%Y", errors="coerce")
        if series.name == "Atualizado em":
            date_str2 = (middle_numbers.astype(str).str.zfill(2) + "/" +
                         first_numbers.astype(str).str.zfill(2) + "/" +
                         last_numbers)
            # Converte a string para datetime no formato %d/%m/%Y
            date_column = pd.to_datetime(date_str2, format="%d/%m/%Y", errors="coerce")
        else:
            if (first_numbers > 12).sum() > 0:
                date_str = first_numbers.astype(str) + "/" + middle_numbers.astype(str) + "/" + last_numbers
                date_column = pd.to_datetime(date_str, format="%d/%m/%Y", errors="coerce")
                # date_column = date_str.apply(lambda x: f"{x[:2]}/{x[2:4]}/{x[4:]}")
            elif (middle_numbers > 12).sum() > 0:
                date_str = middle_numbers.astype(str) + "/" + first_numbers.astype(str) + "/" + last_numbers
                date_column = pd.to_datetime(date_str, format="%d/%m/%Y", errors="coerce")
                # date_column = date_str.apply(lambda x: f"{x[:2]}/{x[2:4]}/{x[4:]}")
            else:
                date_str = first_numbers.astype(str) + "/" + middle_numbers.astype(str) + "/" + last_numbers
                date_column_1 = pd.to_datetime(date_str, dayfirst=False, errors="coerce")
                date_column_2 = pd.to_datetime(date_str, dayfirst=True, errors="coerce")
                date_column = date_column_1 if date_column_1.notna().sum() >= date_column_2.notna().sum() else date_column_2
                # if (first_numbers.max() - first_numbers.min()) >= (middle_numbers.max() - middle_numbers.min()):
                #     date_column = series.dropna().apply(
                #         lambda x: f"{x[:2]}/{x[2:4]}/{x[4:]}" if isinstance(x, str) and len(x) >= 8 else x
                #     )
                # else:
                #     date_column = series.dropna().apply(
                #         lambda x: f"{x[2:4]}/{x[:2]}/{x[4:]}" if isinstance(x, str) and len(x) >= 8 else x
                #     )

        return date_column if date_column.notna().any() else None

    def format_date(date): # TODO ver onde tava usando isso e se não precisa mais
        """Converte datas escritas em texto para dd/mm/yyyy."""
        try:
            parsed_date = pd.to_datetime(date, errors="coerce")
            return parsed_date.strftime('%d/%m/%Y') if not pd.isna(parsed_date) else date
        except Exception:
            return date

    for col in df.columns:
        # Detecta se o nome da coluna sugere uma data
        if any(keyword in col.lower() for keyword in ['data', 'atualizado']):
            sample_values = df[col].dropna().astype(str).sample(min(len(df[col]), 20), random_state=42)

            # TODO ver toda essa parte, se precisa mesmo (se estiver transformando em formato data, não precisa
            # Verifica se a coluna contém apenas valores no formato de data
            if (sample_values.str.fullmatch(date_pattern, na=False).any() or
                    sample_values.str.fullmatch(date_pattern2, na=False).any()):
                date_format = infer_date_format(df[col])
                if date_format is not None and pd.api.types.is_datetime64_any_dtype(date_format):
                    # df[col] = date_format.dt.strftime('%d/%m/%Y')
                    detected_types[col] = "Data"
                    print(f"🗓️ Coluna '{col}' identificada como Data e formatada.")
                    # print(f"Coluna {col} é tipo {type(col)}")
                else:
                    print(f"⚠️ Falha na conversão para datetime na coluna '{col}'")

            # Verifica se há datas escritas em formato de texto (ex: "20 de março de 2023")
            elif sample_values.str.contains('|'.join(meses), case=False, regex=True, na=False).any():
                df[col] = df[col].apply(lambda x: format_date(x) if pd.notna(x) else x)
                detected_types[col] = "Data"
                # print(f"Coluna {col} é tipo {type(col)}")
                print(f"🗓️ Coluna '{col}' identificada como Data e formatada.")

    return df

def detect_account(df, detected_types):
    """Detecta colunas de e-mail, LinkedIn e Instagram, garantindo que a validação seja precisa."""

    print("\n🔍 Detectando colunas de e-mail, LinkedIn e Instagram...")

    # Expressões regulares para identificação
    email_pattern = re.compile(r"^[\wÀ-ÖØ-öø-ÿ._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
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


def normalize_dataframe(df, detected_types):
    """Remove caracteres não alfanuméricos de todas as colunas não identificadas anteriormente."""
    print("🔍 Normalizando colunas - removendo caracteres especiais...")

    def clean_text(value):
        if isinstance(value, str):
            # Remove caracteres que não são letras, números ou espaços
            return re.sub(r'[^a-zA-Z0-9À-ÖØ-öø-ÿ]', '', value)
        return value

    # Criar uma cópia do DataFrame para evitar modificar o original
    df_normalized = df.copy()

    # text_columns = [
    #     col for col in df_normalized.select_dtypes(include=["object"]).columns
    #     if col not in detected_types or detected_types.get(col) == "Data"
    # ]

    normalize_columns = [
        col for col in df_normalized.select_dtypes(include=["object"]).columns
        if detected_types.get(col, "") in ("Data", "Telefone", "CPF")  # Retorna "" se col não existir
    ]

    # Aplicar a normalização apenas nessas colunas
    for col in normalize_columns:
        df_normalized[col] = df_normalized[col].map(clean_text)

    # print(f"✅ Colunas normalizadas: {text_columns}")

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
            total_values = len(df[col])
            unique_count = len(unique_values)
            unique_ratio = unique_count / total_values

            if unique_ratio >= 0.50: #TODO criar uma regra pra considerar se a tabela ref tem menos de 200(?) linhas
                unique_values_dict[col] = unique_values.tolist()
            else:
                sample_size = int(0.30 * unique_count)
                unique_values_dict[col] = pd.Series(unique_values).sample(n=sample_size,
                                                                          random_state=1).tolist()

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

    df = detect_and_format_dates(df, detected_types)
    detected_types = detect_account(df, detected_types)

    detected_types = detect_phone_and_cpf(df, detected_types)
    # df = normalize_dataframe(df, detected_types)

    # Detecta tipos de colunas e obtém valores únicos para colunas de texto
    detected_types, unique_values_dict = detect_column_type(df, detected_types)

    # Corrige colunas classificadas como 'Número com erro'
    df, detected_types = correct_number(df, detected_types)
    if 'Atualizado em' in df.columns:
        # A coluna existe, então você pode realizar a transformação desejada
        df['Atualizado em'] = df['Atualizado em'].apply(
            lambda x: '/'.join([x.split('-')[1], x.split('-')[0], x.split('-')[2]])
        )

    result_df = pd.DataFrame(list(detected_types.items()), columns=['Coluna', 'Tipo'])
    print(f"DF final: {df.head(5).to_string(index=False)}")
    # for col in df.columns:
    #     print(f"Coluna '{col}': {type(col)}")
    # print(f"Lista: {unique_values_dict}")

    return df, result_df, unique_values_dict

#---------------------------FAZER O MATCH DAS COLUNAS---------------------------#
def extract_year(value):
    """Extrai os últimos 4 números da string como ano, se possível."""
    match = re.search(r'(\d{4})$', str(value))  # Procura um conjunto de 4 números no final
    return int(match.group(1)) if match else None  # Converte para inteiro ou retorna None

def date_var(df, column_name, min_valid_percent=0.8):

    # # Filtrar apenas os valores que têm exatamente 8 caracteres
    # valid_dates = df[column_name].dropna().astype(str)
    # valid_dates = valid_dates[valid_dates.str.len() == 8]
    # # print(f"8 digitos: {valid_dates}")
    #
    # # Extrair dia, mês e ano e formatar como DD/MM/YYYY
    # valid_dates = valid_dates.apply(lambda x: f"{x[:2]}/{x[2:4]}/{x[4:]}")
    # # print(f"Extrair: {valid_dates}")
    #
    # # Converter para datetime
    # valid_dates = pd.to_datetime(valid_dates, format="%d/%m/%Y", errors="coerce").dropna()
    # # print(f"Converter: {valid_dates}")
    #
    # # Garantir que `valid_dates` seja uma Series antes de calcular `diff()`
    # valid_dates = pd.Series(valid_dates).sort_values(ignore_index=True)  # Converter para Series e ordenar
    # # print(f"Series: {valid_dates}")
    #
    # # Calcular a variação entre valores consecutivos
    # date_variation = valid_dates.diff().dt.days  # Retorna a diferença diretamente em dias
    # # print(f"Deu certo? {date_variation}")
    # 🔹 1. Imprimir os dados originais antes de qualquer processamento
    print(f"\n📌 Dados originais da coluna '{column_name}':\n{df[column_name]}\n")

    # 🔹 2. Remover valores nulos e converter para string
    valid_dates = df[column_name].dropna().astype(str)

    # 🔹 3. Filtrar apenas os valores que têm exatamente 8 caracteres
    valid_dates_filtered = valid_dates[valid_dates.str.len() == 8]

    # 🔹 4. Verificar a porcentagem de dados válidos
    valid_percent = len(valid_dates_filtered) / len(valid_dates) if len(valid_dates) > 0 else 0

    if valid_percent < min_valid_percent:
        print(f"⚠️ Apenas {valid_percent:.0%} dos dados estão no formato correto. Abortando operação.")
        return pd.Series(dtype="int64")  # Retorna uma Series vazia

    print(f"✅ {valid_percent:.0%} dos dados estão corretos ({len(valid_dates_filtered)} valores). Continuando...\n")

    # 🔹 5. Extrair dia, mês e ano e formatar como DD/MM/YYYY
    valid_dates_filtered = valid_dates_filtered.apply(lambda x: f"{x[:2]}/{x[2:4]}/{x[4:]}")
    print(f"📆 Datas formatadas: \n{valid_dates_filtered}\n")

    # 🔹 6. Converter para datetime
    valid_dates_filtered = pd.to_datetime(valid_dates_filtered, format="%d/%m/%Y", errors="coerce").dropna()
    print(f"📅 Datas convertidas para datetime: \n{valid_dates_filtered}\n")

    # 🔹 7. Garantir que `valid_dates_filtered` seja uma Series e ordenar
    valid_dates_filtered = pd.Series(valid_dates_filtered).sort_values(ignore_index=True)
    print(f"📌 Datas ordenadas: \n{valid_dates_filtered}\n")

    # 🔹 8. Calcular a variação entre valores consecutivos
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

                if name_similarity >= 0.95: #TODO deixa isso?
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
                        normalized_new = re.sub(r'[^a-zA-Z0-9À-ÖØ-öø-ÿ]', '', new_data[new_col])
                        normalized_ref = re.sub(r'[^a-zA-Z0-9À-ÖØ-öø-ÿ]', '', new_data[new_col])
                        current_year = dt.today().year
                        year_new = year_evaluation(new_data[new_col])
                        year_ref = year_evaluation(ref_data[ref_col])
                        print(f"Ano atual: {current_year}, Ano new_data: {year_new}, Ano ref: {year_ref}")

                        # diff_mean = abs((current_year - year_new) - (current_year - year_ref))
                        # diff_median = abs((current_year - new_median) - (current_year - ref_median))
                        #
                        # diff_new = abs(current_year - year_new)  # Diferença do ano atual para new_data
                        # diff_ref = abs(current_year - year_ref)  # Diferença do ano atual para ref_data

                        # Média das diferenças normalizada pelo ano atual
                        data_age = (100 - (abs(year_new - year_ref))) / 100
                        print(f"Coeficiente ano: {data_age}")

                        variation_new = date_var(new_data, new_col)
                        variation_ref = date_var(ref_data, ref_col)

                        if isinstance(variation_new, pd.Series):
                            variation_new = variation_new.mean()
                        if isinstance(variation_ref, pd.Series):
                            variation_ref = variation_ref.mean()

                        variation_diff = abs(variation_new - variation_ref)
                        # Normaliza entre 0 e 1
                        variation_score = 1 - (variation_diff / max(variation_new, variation_ref, 1))
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

            # else:
            #     print("Tipo de dados incompatíveis")

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
    print(f"Colunas sem correspondência em {filename2}: {not_match_new}")
    print(f"Colunas sem correspondência em {filename1}: {not_match_ref}\n")

    return matched_columns

#---------------------------TRANSFORMAR OS DADOS DA TABELA NOVA---------------------------#
def transform_data(new_data, matched_columns):
    print("Iniciando transformação de dados...")

    transformed_data = new_data.rename(columns=matched_columns)
    print(f"Transformed data: {transformed_data}")

    # for ref_col in matched_columns.values():  # Usando os nomes da tabela 1
    #     if ref_col in transformed_data.columns:  # Garante que a coluna existe antes de transformar
    #
    #         if 'telefone fixo' in ref_col.lower():
    #             transformed_data[ref_col] = transformed_data[ref_col].apply(lambda x: format_phone_number(x))
    #             print(f"📱 Números de celular formatados na coluna '{ref_col}'")
    #
    #         if 'celular' in ref_col.lower():
    #             transformed_data[ref_col] = transformed_data[ref_col].apply(lambda x: format_phone_number(x))
    #             print(f"📱 Números de celular formatados na coluna '{ref_col}'")
    #
    #         if 'cpf' in ref_col.lower():
    #             transformed_data[ref_col] = transformed_data[ref_col].apply(lambda x: format_cpf(x))
    #             print(f"🆔 CPF formatado na coluna '{ref_col}'")

    # Aplicar transformações específicas apenas se a coluna existir e corresponder EXATAMENTE ao nome esperado
    # for ref_col in transformed_data.columns:
    #     if ref_col == "Telefone Fixo":
    #         transformed_data[ref_col] = transformed_data[ref_col].apply(lambda x: format_phone_number(x))
    #         print(f"📞 Números de telefone fixo formatados na coluna '{ref_col}'")
    #
    #     if ref_col == "Celular":
    #         transformed_data[ref_col] = transformed_data[ref_col].apply(lambda x: format_phone_number(x))
    #         print(f"📱 Números de celular formatados na coluna '{ref_col}'")
    #
    #     if ref_col == "CPF":
    #         transformed_data[ref_col] = transformed_data[ref_col].apply(lambda x: format_cpf(x))
    #         print(f"🆔 CPF formatado na coluna '{ref_col}'")
    #
    print("Transformação de dados concluída!\n")
    # print(f"Transformed data: {transformed_data}")
    return transformed_data

def format_phone_number(phone):
    if isinstance(phone, str):
        cleaned = re.sub(r'\D', '', phone)  # Remove non-numeric characters
        if len(cleaned) == 11: # TODO ajustar pra considerar numeros com e sem o "55" na frente
            return f'+55 ({cleaned[:2]}) {cleaned[2:7]}-{cleaned[7:]}'
        elif len(cleaned) == 10:
            return f'+55 ({cleaned[:2]}) {cleaned[2:6]}-{cleaned[6:]}'
        else: # TODO alguma coisa errada aqui, que ta passando todas as colunas
            print("Falha ao formatar telefone - não possui nem 11 e nem 10 caractres")
            return None
    else:
        print("Falha ao formatar telefone - falha ao identificar dado")
        return None


def format_cpf(cpf):
    if isinstance(cpf, str):
        cleaned = re.sub(r'\D', '', cpf)
        if len(cleaned) == 11:
            return f'{cleaned[:3]}.{cleaned[3:6]}.{cleaned[6:9]}-{cleaned[9:]}'
        else:
            print(f"Não foi possível formatar o cpf - não tem 11 caracteres")
            return None
    else:
        print("Não foi possível formatar o cpf - falha ao identificar dado")
        return None

#---------------------------JUNTAR DADOS TRANSFORMADOS---------------------------#
def refine_data(ref_data, transformed_data):
    print("Refinando dados na tabela transformada...")

    # print("Duplicados em ref_data:", ref_data.index.duplicated().sum())
    # print("Duplicados em transformed_data:", transformed_data.index.duplicated().sum())
    #
    # print("\nColunas ref_data:", ref_data.columns)
    # print("Colunas transformed_data:", transformed_data.columns)
    #
    # print("\nTipo de índice ref_data:", ref_data.index.dtype)
    # print("Tipo de índice transformed_data:", transformed_data.index.dtype)

    # 🔹 Remover colunas extras em `transformed_data` que não existem em `ref_data`
    transformed_data = transformed_data[[col for col in ref_data.columns if col in transformed_data.columns]].copy()
    # print(f"Transformed data: {transformed_data}")

    # 🔹 Adicionar colunas ausentes em `transformed_data`, preenchendo com "" (ou `None`, se preferir)
    missing_cols = set(ref_data.columns) - set(transformed_data.columns)
    for col in missing_cols:
        transformed_data.loc[:, col] = ""  # ⚠️ Agora usamos .loc para evitar o warning

    # print(f"Transformed data: {transformed_data}")

    # 🔹 Garantir que a ordem das colunas seja a mesma do `ref_data`
    refined_data = transformed_data[ref_data.columns]
    # print(f"Refined data: {refined_data}")

    # print("\n📌 Colunas ref_data:", ref_data.columns.tolist())
    # print("📌 Colunas refined_data:", refined_data.columns.tolist())

    # 🔹 COMPARAÇÃO DAS COLUNAS
    # print("\n🔎 Comparando colunas entre ref_data e refined_data...")
    #
    # column_comparison = {} # TODO a lógica ta errada
    #
    # for col in ref_data.columns:
    #     if col in refined_data.columns:
    #         are_equal = ref_data[col].equals(refined_data[col])
    #         column_comparison[col] = "✅ Iguais" if are_equal else "❌ Diferentes"
    #
    # # 🔹 Imprimir os resultados linha por linha
    # print("\n📊 Resultado da Comparação:")
    # for col, status in column_comparison.items():
    #     print(f"🔹 Coluna '{col}': {status}")

    # # 🔹 Reiniciar os índices antes da fusão para evitar erros de indexação
    # ref_data = ref_data.reset_index(drop=True)
    # transformed_data = transformed_data.reset_index(drop=True)
    #
    # # Mescla os dados, mantendo apenas as colunas de ref_data
    # merged_data = pd.concat([ref_data, transformed_data], ignore_index=True)

    print("Fusão de dados concluída!\n")
    return refined_data

#---------------------------EXECUTAR PROCESSO COMPLETO---------------------------#
def main():
    ref_path = "ref_data.csv"  # Altere para o caminho correto no Bubble
    new_path = "new_data.csv"  # Altere para o caminho correto no Bubble
    output_path = "refined_data.csv"

    print("Carregando arquivos CSV...")
    ref_data = pd.read_csv(ref_path)
    new_data = pd.read_csv(new_path)

    # TODO como não imprimir
    print("📊 Analisando tipos de dados...")
    # 🔹 Executa a função apenas uma vez e armazena os retornos
    df_ref, ref_types, unique_values_dict_ref = analyze_table(ref_data, ref_path)
    df_new, new_types, unique_values_dict_new = analyze_table(new_data, new_path)

    print(ref_types)
    print(new_types)

    matched_columns = match_columns(df_ref, df_new, ref_types, new_types, ref_path, new_path)
    transformed_data = transform_data(df_new, matched_columns)
    refined_data = refine_data(df_ref, transformed_data)

    refined_data.to_csv(output_path, index=False)
    print(f"✅ Dados transformados salvos como: {output_path}")

if __name__ == "__main__":
    main()


















# import pandas as pd
# import re
# from difflib import SequenceMatcher
#
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
#             return None
#
#         first_numbers = extracted[0].dropna().astype(int, errors="ignore")
#         middle_numbers = extracted[1].dropna().astype(int, errors="ignore")
#         last_numbers = extracted[2].dropna().astype(str)
#
#         # Se o primeiro número for maior que 12, assumimos que é DD/MM/YYYY
#         if (first_numbers > 12).sum() > 0:
#             date_str = first_numbers.astype(str) + "/" + middle_numbers.astype(str) + "/" + last_numbers
#             date_column = pd.to_datetime(date_str, format="%d/%m/%Y", errors="coerce")
#         # Se o segundo número (que seria o dia) for maior que 12, assumimos MM/DD/YYYY
#         elif (middle_numbers > 12).sum() > 0:
#             date_str = middle_numbers.astype(str) + "/" + first_numbers.astype(str) + "/" + last_numbers
#             date_column = pd.to_datetime(date_str, format="%d/%m/%Y", errors="coerce")
#         else:
#             date_str = first_numbers.astype(str) + "/" + middle_numbers.astype(str) + "/" + last_numbers
#             date_column_1 = pd.to_datetime(date_str, dayfirst=False, errors="coerce")
#             date_column_2 = pd.to_datetime(date_str, dayfirst=True, errors="coerce")
#             if date_column_1.isna().sum() < date_column_2.isna().sum():
#                 date_column = date_column_1
#             else:
#                 date_column = date_column_2
#
#         if date_column.isna().all():
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
#         column_modified = False
#
#         # Verifica se o nome da coluna contém palavras-chave
#         if any(keyword in col.lower() for keyword in ['data', 'atualizado']):
#             sample_values = new_data[col].dropna().astype(str).sample(min(len(new_data[col]), 20), random_state=42)
#
#             # Usamos fullmatch para garantir que toda a string corresponda ao padrão
#             if sample_values.str.fullmatch(date_pattern, na=False).any():
#                 date_format = infer_date_format(new_data[col])
#                 if date_format is not None and pd.api.types.is_datetime64_any_dtype(date_format):
#                     new_data[col] = date_format.dt.strftime('%d/%m/%Y')
#                     column_modified = True
#                 else:
#                     print(f"⚠️ Falha na conversão para datetime na coluna '{col}'")
#             elif sample_values.str.contains('|'.join(meses), case=False, regex=True, na=False).any():
#                 new_data[col] = new_data[col].apply(lambda x: format_date(x) if pd.notna(x) else x)
#                 column_modified = True
#
#         if column_modified:
#             print(f"🗓️ Coluna '{col}' detectada como data e formatada para dd/mm/aaaa")
#
#     print("📅 Detecção e formatação de datas concluída!\n")
#     return new_data
#
#
# def match_columns(ref_data, new_data, threshold=0.59):
#     matched_columns = {}
#     not_match = []
#     print("Iniciando correspondência de colunas...")
#
#     for ref_col in ref_data.columns:
#         best_match = None
#         best_score = 0
#         best_new_col = None  # Armazena a melhor coluna correspondente da tabela 2
#
#         for new_col in new_data.columns:
#             cleaned_new_col = re.sub(r'[.\-]', '', new_col).lower()
#             cleaned_ref_col = re.sub(r'[.\-]', '', ref_col).lower()
#             name_similarity = SequenceMatcher(None, cleaned_new_col, cleaned_ref_col).ratio()
#
#             if name_similarity >= 0.95:
#                 matched_columns[new_col] = ref_col
#                 print(f"✅ Coluna '{new_col}' foi renomeada para '{ref_col}' por similaridade de nome {name_similarity:.2f}")
#                 break  # Se a similaridade for alta o suficiente, já garantimos o match
#
#             data_similarity = 0
#             if new_col in new_data and ref_col in ref_data and new_data[new_col].dtype == ref_data[ref_col].dtype:
#                 common_values = set(new_data[new_col].dropna().astype(str)) & set(ref_data[ref_col].dropna().astype(str))
#                 total_values = set(new_data[new_col].dropna().astype(str)) | set(ref_data[ref_col].dropna().astype(str))
#
#                 if total_values:
#                     data_similarity = len(common_values) / len(total_values)
#
#             overall_score = (name_similarity * 0.5) + (data_similarity * 0.5)
#
#             # print(f"Comparando '{new_col}' com '{ref_col}':\n"
#             #       f"  - Similaridade de nome: {name_similarity:.2f}\n"
#             #       f"  - Similaridade de dados: {data_similarity:.2f}\n"
#             #       f"  - Score final: {overall_score:.2f}")
#
#             if overall_score > best_score:
#                 best_score = overall_score
#                 best_match = ref_col
#                 best_new_col = new_col  # Armazena a coluna correspondente
#
#         if best_match and best_score >= threshold:
#             matched_columns[best_new_col] = best_match
#             print(f"✅ Coluna '{best_new_col}' foi renomeada para '{best_match}' com score {best_score:.2f}")
#         else:
#             if best_match is None:  # Só adiciona à lista de erro se realmente não encontrou um match
#                 not_match.append(ref_col)
#                 print(f"❌ ERRO. Nenhuma coluna correspondente encontrada para '{ref_col}'")
#
#     print("Correspondência de colunas concluída!\n")
#     print(f"Colunas sem correspondência: {not_match}\n")
#     return matched_columns
#
#
#
# def transform_data(new_data, matched_columns):
#     print("Iniciando transformação de dados...")
#
#     transformed_data = new_data.rename(columns=matched_columns)
#
#     for ref_col in matched_columns.values():  # Usando os nomes da tabela 1
#         if ref_col in transformed_data.columns:  # Garante que a coluna existe antes de transformar
#
#             if 'email' in ref_col.lower():
#                 transformed_data[ref_col] = transformed_data[ref_col].apply(
#                     lambda x: x if isinstance(x, str) and '@' in x else None)
#                 print(f"📧 E-mails validados na coluna '{ref_col}'")
#
#             if 'telefone fixo' in ref_col.lower():
#                 transformed_data[ref_col] = transformed_data[ref_col].apply(lambda x: format_phone_number(x))
#                 print(f"📱 Números de celular formatados na coluna '{ref_col}'")
#
#             if 'celular' in ref_col.lower():
#                 transformed_data[ref_col] = transformed_data[ref_col].apply(lambda x: format_phone_number(x))
#                 print(f"📱 Números de celular formatados na coluna '{ref_col}'")
#
#             if 'linkedin' in ref_col.lower():
#                 transformed_data[ref_col] = transformed_data[ref_col].apply(
#                     lambda x: x if isinstance(x, str) and x.startswith("http://linkedin.com/") else None)
#                 print(f"🔗 Links do LinkedIn validados na coluna '{ref_col}'")
#
#             if 'instagram' in ref_col.lower():
#                 transformed_data[ref_col] = transformed_data[ref_col].apply(
#                     lambda x: x if isinstance(x, str) and x.startswith("@") else None)
#                 print(f"📷 Handles do Instagram validados na coluna '{ref_col}'")
#
#             if 'rg' in ref_col.lower():
#                 transformed_data[ref_col] = transformed_data[ref_col].apply(lambda x: format_rg(x))
#                 print(f"🆔 RG formatado na coluna '{ref_col}'")
#
#             if 'cpf' in ref_col.lower():
#                 transformed_data[ref_col] = transformed_data[ref_col].apply(lambda x: format_cpf(x))
#                 print(f"🆔 CPF formatado na coluna '{ref_col}'")
#
#     print("Transformação de dados concluída!\n")
#     return transformed_data
#
# def format_phone_number(phone):
#     if isinstance(phone, str):
#         cleaned = re.sub(r'\D', '', phone)  # Remove non-numeric characters
#         if len(cleaned) == 11:
#             return f'+55 ({cleaned[:2]}) {cleaned[2:7]}-{cleaned[7:]}'
#         elif len(cleaned) == 10:
#             return f'+55 ({cleaned[:2]}) {cleaned[2:6]}-{cleaned[6:]}'
#     return None
#
#
# def format_rg(rg):
#     if isinstance(rg, str):
#         cleaned = re.sub(r'\D', '', rg)
#         if 7 <= len(cleaned) <= 9:
#             return int(cleaned)  # Converte para número inteiro
#     return None
#
#
# def format_cpf(cpf):
#     if isinstance(cpf, str):
#         cleaned = re.sub(r'\D', '', cpf)
#         if len(cleaned) == 11:
#             return f'{cleaned[:3]}.{cleaned[3:6]}.{cleaned[6:9]}-{cleaned[9:]}'
#     return None
#
#
# def merge_data(ref_data, transformed_data):
#     print("Iniciando fusão de dados...")
#     merged_data = pd.concat([ref_data, transformed_data], ignore_index=True)
#     print("Fusão de dados concluída!\n")
#     return merged_data
#
#
# def main():
#     ref_path = "ref_data.csv"  # Altere para o caminho correto
#     new_path = "new_data.csv"  # Altere para o caminho correto
#     output_path = "merged_data.csv"
#
#     print("Carregando arquivos CSV...")
#     ref_data = pd.read_csv(ref_path)
#     new_data = pd.read_csv(new_path)
#     print("Arquivos carregados com sucesso!\n")
#
#     new_data = detect_and_format_dates(new_data)  # Formatar datas antes da correspondência
#
#     matched_columns = match_columns(ref_data, new_data)
#     transformed_data = transform_data(new_data, matched_columns)
#     merged_data = merge_data(ref_data, transformed_data)
#
#     merged_data.to_csv(output_path, index=False)
#     print(f"Dados mesclados salvos em {output_path}")
#
#
# if __name__ == "__main__":
#     main()
#
#
#
#
#
#
#
#
#
#
#
#
# # import pandas as pd
# # import re
# # from fuzzywuzzy import fuzz
# # from fuzzywuzzy import process
# # import os
# #
# # # 📂 Carregar as Tabelas
# # caminho_tabela_1 = "ref_data.csv"  # Tabela de referência
# # caminho_tabela_2 = "new_data.csv"  # Tabela com novos dados
# #
# # df_padrao = pd.read_csv(caminho_tabela_1)
# # df_novos = pd.read_csv(caminho_tabela_2)
# #
# # # 📌 1. Mapeamento de Colunas com Fuzzy Matching
# # mapeamento_colunas = {}
# # colunas_ref = df_padrao.columns
# # colunas_novas = df_novos.columns
# #
# # for coluna_nova in colunas_novas:
# #     match, score = process.extractOne(coluna_nova, colunas_ref, scorer=fuzz.token_sort_ratio)
# #     if score > 80:  # Threshold de 80% de similaridade
# #         mapeamento_colunas[coluna_nova] = match
# #     else:
# #         mapeamento_colunas[coluna_nova] = None  # Nenhum match encontrado
# #
# # # 🔹 Ajuste manual para colunas críticas
# # mapeamento_colunas["Número de Celular"] = "Celular"
# # mapeamento_colunas["Telefone Fixo"] = "Telefone Fixo"
# #
# # # 📌 2. Renomear colunas conforme o match encontrado
# # df_novos.rename(columns=mapeamento_colunas, inplace=True)
# #
# # # 📌 3. Ajustar Formato dos Telefones
# # def formatar_telefone(numero, tipo):
# #     """ Formata número de telefone fixo e celular conforme o tipo. """
# #     if pd.isna(numero) or numero.strip() == "":
# #         return None
# #     numero = re.sub(r"\D", "", str(numero))  # Remove caracteres não numéricos
# #     if tipo == "fixo" and len(numero) == 10:  # Exemplo: 1199999999 -> +55 (11) 9999-9999
# #         return f"+55 ({numero[:2]}) {numero[2:6]}-{numero[6:]}"
# #     elif tipo == "celular" and len(numero) == 11:  # Exemplo: 11999999999 -> +55 (11) 99999-9999
# #         return f"+55 ({numero[:2]}) {numero[2:7]}-{numero[7:]}"
# #     return None
# #
# # if "Telefone Fixo" in df_novos.columns:
# #     df_novos["Telefone Fixo"] = df_novos["Telefone Fixo"].apply(lambda x: formatar_telefone(x, "fixo"))
# # if "Celular" in df_novos.columns:
# #     df_novos["Celular"] = df_novos["Celular"].apply(lambda x: formatar_telefone(x, "celular"))
# #
# # # 📌 4. Ajustar Formato de CPF, RG e E-mail
# # def formatar_cpf(cpf):
# #     cpf = re.sub(r"\D", "", str(cpf))
# #     return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}" if len(cpf) == 11 else None
# #
# # def formatar_rg(rg):
# #     rg = re.sub(r"\D", "", str(rg))
# #     return rg if 7 <= len(rg) <= 9 else None
# #
# # def validar_email(email):
# #     return email if pd.notna(email) and re.match(r"[^@]+@[^@]+\.[^@]+", str(email)) else None
# #
# # if "CPF" in df_novos.columns:
# #     df_novos["CPF"] = df_novos["CPF"].apply(formatar_cpf)
# # if "RG" in df_novos.columns:
# #     df_novos["RG"] = df_novos["RG"].apply(formatar_rg)
# # if "E-mail" in df_novos.columns:
# #     df_novos["E-mail"] = df_novos["E-mail"].apply(validar_email)
# #
# # # 📌 5. Garantir que Novos Valores de Listas Sejam Adicionados
# # listas_com_opcoes = {
# #     "Categoria de Stakeholder": list(df_padrao["Categoria de Stakeholder"].dropna().unique()),
# #     "Nível de Relacionamento": list(df_padrao["Nível de Relacionamento"].dropna().unique()),
# #     "Canal Preferido": list(df_padrao["Canal Preferido"].dropna().unique()),
# #     "Estado Civil": list(df_padrao["Estado Civil"].dropna().unique()),
# #     "Gênero": list(df_padrao["Gênero"].dropna().unique()),
# #     "Função de Compra": list(df_padrao["Função de Compra"].dropna().unique()),
# #     "Função de Impacto": list(df_padrao["Função de Impacto"].dropna().unique()),
# #     "Função de Formalização": list(df_padrao["Função de Formalização"].dropna().unique()),
# #     "Função de Faturamento": list(df_padrao["Função de Faturamento"].dropna().unique()),
# # }
# #
# # for coluna, valores in listas_com_opcoes.items():
# #     if coluna in df_novos.columns:
# #         df_novos[coluna] = df_novos[coluna].apply(lambda x: x if x in valores else (valores.append(x) or x))
# #
# # # 📌 6. Adicionar os Novos Dados na Tabela 1
# # df_final = pd.concat([df_padrao, df_novos], ignore_index=True)
# #
# # # 📌 7. Salvar os Dados Processados
# # caminho_saida = "dados_processados/dados_limpos.csv"
# # os.makedirs("dados_processados", exist_ok=True)
# # df_final.to_csv(caminho_saida, index=False)
# #
# # print(f"✅ Dados processados e salvos em: {caminho_saida}")
