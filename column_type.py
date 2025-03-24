from code_sup import VALID_DDD, meses
import pandas as pd
import re


def detect_and_format_dates(df, detected_types):
    """Detecta colunas de data e converte para o formato dd/mm/aaaa."""
    print("🔍 Detectando e formatando colunas de data...")

    date_pattern = re.compile(r'^\s*(\d{1,2})[-/.\s](\d{1,2})[-/.\s](\d{2,4})\s*$')

    def infer_date_format(series):
        """Determina o formato da data e a converte corretamente para datetime."""
        extracted = series.str.extract(date_pattern)
        if extracted.isnull().all().all():
            return None

        first_numbers = extracted[0].dropna().astype("Int64")
        middle_numbers = extracted[1].dropna().astype("Int64")
        last_numbers = extracted[2].dropna().astype(str)

        if (first_numbers > 12).sum() > 0:
            date_str = first_numbers.astype(str) + "/" + middle_numbers.astype(str) + "/" + last_numbers
            date_column = pd.to_datetime(date_str, format="%d/%m/%Y", errors="coerce")
        elif (middle_numbers > 12).sum() > 0:
            date_str = middle_numbers.astype(str) + "/" + first_numbers.astype(str) + "/" + last_numbers
            date_column = pd.to_datetime(date_str, format="%d/%m/%Y", errors="coerce")
        else:
            date_str = first_numbers.astype(str) + "/" + middle_numbers.astype(str) + "/" + last_numbers
            date_column_1 = pd.to_datetime(date_str, dayfirst=False, errors="coerce")
            date_column_2 = pd.to_datetime(date_str, dayfirst=True, errors="coerce")
            date_column = date_column_1 if date_column_1.notna().sum() >= date_column_2.notna().sum() else date_column_2

        return date_column if date_column.notna().any() else None

    def format_date(date):
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

            # Verifica se a coluna contém apenas valores no formato de data
            if sample_values.str.fullmatch(date_pattern, na=False).any():
                date_format = infer_date_format(df[col])
                if date_format is not None and pd.api.types.is_datetime64_any_dtype(date_format):
                    df[col] = date_format.dt.strftime('%d/%m/%Y')
                    detected_types[col] = "Data"
                    print(f"🗓️ Coluna '{col}' identificada como Data e formatada.")
                else:
                    print(f"⚠️ Falha na conversão para datetime na coluna '{col}'")
            # Verifica se há datas escritas em formato de texto (ex: "20 de março de 2023")
            elif sample_values.str.contains('|'.join(meses), case=False, regex=True, na=False).any():
                df[col] = df[col].apply(lambda x: format_date(x) if pd.notna(x) else x)
                detected_types[col] = "Data"
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


def normalize_dataframe(df):
    """Remove caracteres não alfanuméricos de todas as colunas não identificadas anteriormente."""
    print("🔍 Normalizando colunas removendo caracteres especiais...")

    def clean_text(value):
        if isinstance(value, str):
            # Remove caracteres que não são letras, números ou espaços
            return re.sub(r'[^a-zA-Z0-9À-ÖØ-öø-ÿ\s]', '', value)
        return value

    # Aplicamos a limpeza apenas nas colunas de texto
    df_normalized = df.copy()
    for col in df_normalized.select_dtypes(include=["object"]).columns:
        df_normalized[col] = df_normalized[col].map(clean_text)

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
    """Define tipos de coluna restantes como 'Número' ou 'Texto'."""
    print("🔍 Detectando colunas restantes como número ou texto...")

    for col in df.columns:
        if col not in detected_types:
            if pd.to_numeric(df[col], errors='coerce').notna().all():
                detected_types[col] = "Número"
            else:
                detected_types[col] = "Texto"

    for col, col_type in detected_types.items():
        print(f"📊 Coluna '{col}' identificada como {col_type}.")

    return detected_types

def analyze_table(df):
    """Executa todas as etapas na sequência correta."""
    detected_types = {}

    df = detect_and_format_dates(df, detected_types)
    detected_types = detect_account(df, detected_types)

    df = normalize_dataframe(df)
    detected_types = detect_phone_and_cpf(df, detected_types)

    detected_types = detect_column_type(df, detected_types)

    result_df = pd.DataFrame(list(detected_types.items()), columns=['Coluna', 'Tipo'])
    return result_df

def main():
    ref_path = "new_data.csv"

    print("📂 Carregando arquivo CSV...")
    df = pd.read_csv(ref_path)
    print("✅ Arquivo carregado!\n")

    result = analyze_table(df)
    print("\n📊 Resultado final:")
    print(result)

if __name__ == "__main__":
    main()
