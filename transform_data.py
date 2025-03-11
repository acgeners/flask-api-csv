from code_sup import VALID_DDD, months, month_translation
import pandas as pd
import re
from difflib import SequenceMatcher
from dateutil import parser

#---------------------------IDENTIFICAR PLANILHA---------------------------#
def classificar_df(df) -> str:
    """
    Classifica um DataFrame de acordo com suas colunas.

    Retorna:
        - "Pessoa" se contiver as colunas "rg" e "cpf".
        - "Empresa" se contiver as colunas "cnpj" e "cnae".
        - "Negócio" se contiver as colunas "temperatura" e "propriedade".
        - "Desconhecido" se não atender a nenhum dos critérios.
    """

    criterios = {
        "Pessoa": {"rg", "cpf"},
        "Empresa": {"cnpj", "cnae"},
        "Negócio": {"temperatura", "propriedade"}
    }

    # Criar um conjunto temporário de colunas formatadas, sem alterar o df original
    colunas_formatadas = {re.sub(r'\W+', '', col).lower() for col in df.columns}

    for categoria, colunas_necessarias in criterios.items():
        if colunas_necessarias.issubset(colunas_formatadas):
            return categoria

    return "Desconhecido"

def dd_list_columns(df):
    # Identificar colunas que terminam com " (lista)"
    dd_lists = [col for col in df.columns if col.endswith(" (lista)")]

    # Criar uma lista com os nomes sem o sufixo
    cleaned_dd_names = [col.replace(" (lista)", "") for col in dd_lists]

    # Criar um dicionário de mapeamento
    rename_dd_columns = dict(zip(dd_lists, cleaned_dd_names))

    # Renomear colunas no DataFrame
    df.rename(columns=rename_dd_columns, inplace=True)

    return df, cleaned_dd_names

#---------------------------AVALIAR COLUNAS E IDENTIFICAR TIPO---------------------------#

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
                dd_count += 1
            elif second > 12:
                mm_count += 1

    if dd_count > mm_count:
        return True
    elif mm_count > dd_count:
        return False
    else:
        return True


def is_potential_date(value):
    """Verifica se um valor pode ser uma data, analisando se contém separadores ou nomes de meses."""
    value_str = str(value)

    if re.search(r"[-/.]", value_str):
        return True

    if re.search(months, value_str, re.IGNORECASE):
        return True

    return False

def replace_months(value):
    """Substitui os meses em português por inglês para facilitar a conversão de datas."""
    match = re.search(months, value, re.IGNORECASE)
    if match:
        pt_month = match.group(0)  # Nome do mês encontrado
        en_month = month_translation.get(pt_month.lower(), pt_month)  # Traduz se possível
        value = value.replace(pt_month, en_month)
    return value


def is_date(value, dayfirst=True):
    """Tenta converter um valor para datetime, retornando True se for possível."""
    value_str = str(value).strip()

    if value_str.isdigit() and len(value_str) == 4:
        year = int(value_str)
        return 1900 <= year <= 2100

    if not re.search(r"[-/.]", value_str) and not re.search(months, value_str, re.IGNORECASE):
        return False

    try:
        value_str = replace_months(value_str)  # Aplicando a substituição antes da conversão
        parsed = parser.parse(value_str, dayfirst=dayfirst)
        if 1900 <= parsed.year <= 2100:
            return True
        return False
    except (ValueError, TypeError):
        return False


def convert_to_standard_date(value, dayfirst=True):
    """Converte qualquer formato de data para o formato dd/mm/aaaa garantindo a interpretação correta."""
    try:
        value = replace_months(value)  # Aplicando a substituição antes da conversão
        parsed_date = parser.parse(value, dayfirst=dayfirst)
        formatted_date = parsed_date.strftime('%d/%m/%Y')
        return formatted_date
    except (ValueError, TypeError):
        return value


def detect_and_format_dates(df, detected_types):
    print("\n🔍 Detectando e formatando colunas de data...")
    for col in df.columns:

        non_empty = df[col].dropna()
        non_empty = non_empty[non_empty.astype(str).str.strip() != '']

        potential_dates = non_empty.astype(str).apply(is_potential_date).sum()

        if potential_dates < len(non_empty) * 0.9:
            continue

        is_date_valid = non_empty.astype(str).apply(lambda x: is_date(x, dayfirst=True)).mean()

        if is_date_valid > 0.9:
            dayfirst_setting = detect_date_format(non_empty)
            print(f"• Coluna '{col}' identificada como 'Data' e será convertida.")

            df[col] = df[col].astype('object')
            df.loc[non_empty.index, col] = non_empty.astype(str).apply(
                lambda x: convert_to_standard_date(x, dayfirst=dayfirst_setting))

            detected_types[col] = "Data"

    return df


def detect_address(df, detected_types, threshold=0.8):
    print("\n🔍 Detectando colunas de endereço...")
    def is_address(text):
        """
        Evaluates whether a given text is likely to be an address.
        Returns True if it matches address patterns, otherwise False.
        """
        if not isinstance(text, str) or len(text) < 5:
            return False  # Ignore invalid or too short strings

        # Common address keywords
        street_pattern = r'\b(Rua|Av\.?|Avenida|Rodovia|Estrada|Praça|Travessa|Alameda|R\.)\b'
        number_pattern = r'\b\d{1,5}\b'  # Numbers (addresses often have numbers)
        cep_pattern = r'\b\d{5}-\d{3}\b'  # Brazilian postal code format (CEP)
        uf_pattern = r'\b[A-Z]{2}\b'  # State abbreviation (SP, RJ, etc.)
        neighborhood_city_pattern = r'[-,]\s*[A-Za-zÀ-ÿ\s]+'

        score = 0

        # Check for street-related words
        if re.search(street_pattern, text, re.IGNORECASE):
            score += 0.3

        # Check for numbers
        if re.search(number_pattern, text):
            score += 0.2

        # Check for CEP
        if re.search(cep_pattern, text):
            score += 0.2

        # Check for State (UF)
        if re.search(uf_pattern, text):
            score += 0.1

        # Check for neighborhood or city patterns
        if re.search(neighborhood_city_pattern, text):
            score += 0.2

        return score >= 0.5  # Considera endereço se a pontuação for 0.5 ou mais

    for col in df.columns:
        valid_count = df[col].dropna().astype(str).apply(is_address).sum()  # Conta quantas linhas são endereços
        total_count = df[col].notna().sum()  # Conta total de valores não nulos

        if total_count > 0 and (
                valid_count / total_count) >= threshold:  # Verifica se >= 80% das linhas são endereços
            print(f"• Coluna '{col}' identificada como Endereço.")
            detected_types[col] = "Endereço"

    return detected_types

def detect_finance(df, detected_types, threshold=0.8):
    print("\n🔍 Detectando colunas de valores monetários e ranges de valores...")

    def is_financial(text):
        if not isinstance(text, str) or len(text) < 2:
            return False, False  # Retorna duas flags: (é valor simples, é range)

        # Se o valor for um número puro e tiver muitos dígitos, assume que é um ID
        if text.isdigit() and len(text) >= 9:
            return False, False  # Provavelmente um ID, não dinheiro

        # Se o valor for uma probabilidade (entre 0 e 1), não é dinheiro
        try:
            num_value = float(text.replace(",", "."))  # Converter para float
            if 0 <= num_value <= 1:
                return False, False  # Provavelmente uma probabilidade
        except ValueError:
            pass  # Se der erro, continua a verificação normal

        # Símbolos de moeda e palavras numéricas
        currency_symbols = r'(R\$|\$|BRL|USD|€|£|¥|CAD|AUD)'  # Moedas comuns
        word_numbers = r'(\bmilhão\b|\bbilhão\b|\bmilhões\b|\bbilhões\b|\bmil\b)'  # "milhão", "bilhão", etc.

        # Padrão para números formatados (ex: 1.000.000,00 ou 1,000,000.00)
        number_pattern = r'(\d{1,3}(\.\d{3})*,\d{2}|\d{1,3}(,\d{3})*\.\d{2})'

        # Indicadores de intervalo: "-" ou palavras como "até"
        range_indicators = r'(-|\+|\baté\b|\be\b)'  # "Até 360.000", "360.000 - 4.800.000", etc.

        # Verificações
        has_currency = bool(re.search(currency_symbols, text, re.IGNORECASE))
        has_word_number = bool(re.search(word_numbers, text, re.IGNORECASE))
        has_formatted_number = bool(re.search(number_pattern, text))
        has_range_indicator = bool(re.search(range_indicators, text, re.IGNORECASE))

        # Se tem moeda ou palavra numérica + número, é valor financeiro
        is_value = (has_currency or has_word_number) and has_formatted_number

        # Se também tem um indicador de intervalo, é um range de valores
        is_range = is_value and has_range_indicator

        return is_value, is_range

    for col in df.columns:
        if col in detected_types:
            continue  # Pula colunas já processadas

        # Se a coluna se chama exatamente "Valor", define como "Valor"
        if col.lower() == "valor":
            detected_types[col] = "Valor"
            print(f"✔ Coluna '{col}' automaticamente classificada como 'Valor'.")
            continue  # Pula para a próxima coluna, pois já foi processada

        valid_values = df[col].dropna().astype(str).apply(is_financial)
        total_count = df[col].notna().sum()

        value_count = sum(1 for v, r in valid_values if v and not r)  # Apenas valores simples
        range_count = sum(1 for v, r in valid_values if r)  # Apenas ranges de valores

        if total_count > 0:
            value_ratio = value_count / total_count
            range_ratio = range_count / total_count

            if range_ratio >= threshold:
                print(f"• Coluna '{col}' identificada como Range de Valores.")
                detected_types[col] = "Range de valores"
            elif value_ratio >= threshold:
                print(f"• Coluna '{col}' identificada como Valor Monetário.")
                detected_types[col] = "Valor"

    return detected_types


def transform_percent(df, threshold=0.8):
    percent_pattern = re.compile(r'^\s*(\d+[.,]?\d*)\s*%\s*$')
    mod_columns = []

    for coluna in df.columns:
        valores = df[coluna].dropna()  # Remove valores NaN para análise
        total = len(valores)
        if total == 0:
            continue

        percent_amount = sum(bool(percent_pattern.match(str(valor))) for valor in valores)
        percent_prop = percent_amount / total

        if percent_prop >= threshold:
            mod_columns.append(coluna)

            # Converter para formato decimal
            def convert_decimal(valor):
                match = percent_pattern.match(str(valor))
                if match:
                    numero = match.group(1).replace(',', '.')  # Substitui ',' por '.' para conversão correta
                    return float(numero) / 100  # Converte para decimal
                return None  # Mantém NaN para valores inválidos

            df[coluna] = df[coluna].apply(convert_decimal)

    return df

def format_phone(value):
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
        print(f"Falha ao formatar telefone na coluna {value} - falha ao identificar dado")
        return None

def format_cpf(value):
    if isinstance(value, str):
        if len(value) == 11:
            return f'{value[:3]}.{value[3:6]}.{value[6:9]}-{value[9:]}'
        else:
            print(f"Não foi possível formatar o cpf - não tem 11 caracteres")
            return None
    else:
        print("Não foi possível formatar o cpf - falha ao identificar dado")
        return None

def format_cnpj(value):
    if isinstance(value, str):
        digits = re.sub(r'\D', '', value)  # Remove qualquer caractere que não seja número
        if len(digits) == 14:
            return f'{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}'
        else:
            print("Não foi possível formatar o CNPJ - não tem 14 caracteres")
            return None
    else:
        print("Não foi possível formatar o CNPJ - falha ao identificar dado")
        return None

def format_cnae(value):
    if isinstance(value, str):
        digits = re.sub(r'\D', '', value)  # Remove qualquer caractere que não seja número
        if len(digits) == 7:
            return f'{digits[:2]}.{digits[2:4]}-{digits[4]}/{digits[5:]}'
        else:
            print("Não foi possível formatar o CNAE - não tem 7 caracteres")
            return None
    else:
        print("Não foi possível formatar o CNAE - falha ao identificar dado")
        return None

def format_value(value):
    if isinstance(value, (int, float)):
        return str(int(value))  # Se for número puro, retorna apenas o inteiro como string

    if not isinstance(value, str):
        return value  # Se não for string ou número, retorna sem alterações

    # Remover símbolos de moeda, letras e espaços
    value = re.sub(r'[^\d.,]', '', value)  # Mantém apenas números, pontos e vírgulas

    # Se for um número inteiro puro (ex: "450000"), retorna apenas o número
    if value.isdigit():
        return value

    # Se o formato for americano (ex: "260,000.00"), converter para o formato correto
    if re.search(r'\d{1,3},\d{3}\.\d{2}', value):
        value = value.replace(',', '').split('.')[0]  # Remove ',' e corta os centavos

    # Se for um número no formato brasileiro (ex: "1.000.000,00"), remover pontuação e centavos
    if re.match(r'^\d{1,3}(\.\d{3})*,\d{2}$', value):
        value = value.rsplit(',', 1)[0]  # Remove a parte decimal (centavos)
        value = value.replace('.', '')  # Remove pontos dos milhares

    return value  # Retorna o número formatado

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


# Função corrigida para validar CNPJ
def is_valid_cnpj(value):
    """Verifica se um valor é um CNPJ válido seguindo o algoritmo da Receita Federal."""
    digits = re.sub(r'\D', '', str(value))

    if len(digits) != 14 or digits == digits[0] * 14:
        return None

    def calcular_digito(base):
        pesos = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2] if len(base) == 12 else [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        soma = sum(int(base[i]) * pesos[i] for i in range(len(base)))
        resto = soma % 11
        return '0' if resto < 2 else str(11 - resto)

    base_cnpj = digits[:12]
    digito1 = calcular_digito(base_cnpj)
    digito2 = calcular_digito(base_cnpj + digito1)

    return "CNPJ" if digits[-2:] == f"{digito1}{digito2}" else None

def is_valid_cnae(value):
    """Verifica se um valor é um código CNAE válido."""
    digits = re.sub(r'\D', '', str(value))
    return "CNAE" if len(digits) == 7 else None  # CNAE tem 7 dígitos

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

def detect_identifiers(df, detected_types):
    """
    Detecta se as colunas do DataFrame contêm emails, LinkedIn, Instagram, Sites, CPF, CNPJ. CNAE ou Telefone.
    Se mais da metade dos valores forem de um tipo específico, a coluna será categorizada.
    """
    print("\n🔍 Detectando colunas de identificadores: \n→ Site, E-mail, LinkedIn, Instagram\n→ CPF, CNPF, CNAE, Telefone")

    # Expressões regulares para identificação
    patterns = {
        "E-mail": re.compile(r'^[\w.-]+@[\w.-]+\.\w{2,}$'),
        "Linkedin": re.compile(r'^(https?://)?(www\.)?linkedin\.com/in/[^/]+/?$'),
        "Instagram": re.compile(r'^(@[\w.]+|https?://(www\.)?instagram\.com/[^/]+/?)$'),
        "Site": re.compile(r'^(https?://)?(www\.)?[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$')
    }

    for col in df.columns:
        if col not in detected_types and df[col].dtype == 'object':
            values = df[col].dropna().astype(str).str.strip()  # Remove espaços invisíveis

            total_values = len(values)
            if total_values == 0:
                continue  # Pula colunas vazias

            # Contagem de correspondências para expressões regulares
            regex_matches = {key: values.str.match(patterns[key]).sum() for key in patterns}

            cpf_results = values.apply(is_valid_cpf)
            phone_results = values.apply(is_phone_number)
            cnpj_results = values.apply(is_valid_cnpj)
            cnae_results = values.apply(is_valid_cnae)

            cpf_matches = cpf_results.eq("CPF").sum()
            phone_matches = phone_results.eq("Telefone").sum()
            cnpj_matches = cnpj_results.eq("CNPJ").sum()
            cnae_matches = cnae_results.eq("CNAE").sum()


            # Combinar todas as contagens
            matches = {**regex_matches, "CPF": cpf_matches, "Telefone": phone_matches,
                       "CNPJ": cnpj_matches, "CNAE": cnae_matches}

            # Verifica qual categoria tem mais de 80% de correspondência
            for tipo, count in matches.items():
                # print(f"Coluna {col}: count: {count}, total: {total_values}")
                if count / total_values > 0.8:
                    detected_types[col] = tipo
                    print(f"•  Coluna '{col}' identificada como {tipo}.")
                    break  # Se uma categoria for detectada, não precisa verificar as outras


    return detected_types

def format_df(df, detected_types):
    """Remove caracteres não alfanuméricos de todas as colunas não identificadas anteriormente."""
    print("\n🔍 Formatando colunas - removendo caracteres especiais...")

    def clean_column(value):
        if isinstance(value, str):
            if not value.strip():
                return value  # Retorna o valor sem alterações se for vazio ou conter só espaços
            return re.sub(r'\D', '', value)
        return value

    def clean_gender(value):
        if isinstance(value, str):
            # Essa expressão remove "(a)" ou "(o)" no final da string, possivelmente precedido por espaços
            return re.sub(r'\s*\([ao]\)$', '', value)
        return value

    # Criar uma cópia do DataFrame para evitar modificar o original
    df_formated = df.copy()

    format_columns = [
        col for col in df_formated.select_dtypes(include=["object"]).columns
        if detected_types.get(col, "") in ("Telefone", "CPF", "CNPJ", "CNAE")  # Retorna "" se col não existir
    ]

    format_txt_columns = [
        col for col in df_formated.select_dtypes(include=["object"]).columns
        if detected_types.get(col, "") == "Texto"
    ]

    format_values = [
        col for col in df_formated.select_dtypes(include=["object"]).columns
        if detected_types.get(col, "") == "Valor"
    ]

    # Aplicar a formatação apenas nessas colunas
    for col in format_columns:
        # Primeiro, aplica uma limpeza nos textos
        df_formated[col] = df_formated[col].map(clean_column)
        # Em seguida, formata de acordo com o tipo detectado
        if detected_types.get(col, "") == "Telefone":
            df_formated[col] = df_formated[col].map(format_phone)
        elif detected_types.get(col, "") == "CPF":
            df_formated[col] = df_formated[col].map(format_cpf)
        elif detected_types.get(col, "") == "CNPJ":
            df_formated[col] = df_formated[col].map(format_cnpj)
        elif detected_types.get(col, "") == "CNAE":
            df_formated[col] = df_formated[col].map(format_cnae)

    for col in format_txt_columns:
            df_formated[col] = df_formated[col].map(clean_gender)

    for col in format_values:
        df_formated[col] = df_formated[col].map(format_value)
        print(f"Coluna {col}: \n{df_formated[col]}")

    print(f"✅ Colunas formatadas: {format_columns}")

    return df_formated

def detect_column_type(df, detected_types):
    """Define tipos de coluna restantes como 'Número', 'Número com erro' ou 'Texto'.
       Para colunas de texto, retorna uma lista de valores únicos conforme a proporção especificada."""

    print("\n🔍 Detectando colunas restantes como número ou texto...")

    unique_values_dict = {}
    left_categories = {"Null", "Número", "Número com erro", "Texto"}

    for col in df.columns:
        if col not in detected_types:
            # Primeiro verifica se a coluna está completamente vazia
            if df[col].dropna().empty:
                detected_types[col] = "Null"
                continue

            # Verifica se todos os valores não-nulos contêm apenas dígitos
            all_numeric = df[col].dropna().apply(lambda x: str(x).isdigit()).all()

            numeric_ratio = df[col].dropna().apply(lambda x: str(x).isdigit()).mean()

            if all_numeric:
                detected_types[col] = "Número"
            elif numeric_ratio >= 0.95:  # Ajuste aqui conforme necessário
                detected_types[col] = "Número com erro"
            else:
                detected_types[col] = "Texto"

        # Análise adicional para colunas de texto
        if detected_types[col] == "Texto":
            unique_values = df[col].dropna().unique()  # Obtém valores únicos, excluindo NaN

            unique_values_dict[col] = unique_values.tolist()

    for col, col_type in detected_types.items():
        if col_type in left_categories:
            print(f"• Coluna '{col}' identificada como {col_type}.")

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
    print(f"\nAnalisando dados em: {filename}\n")

    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.expand_frame_repr', False)

    detected_types = {}

    df = detect_and_format_dates(df, detected_types)
    # print(f"\nDF após transformar datas: \n{df.head(5).to_string(index=False)}")

    detected_types = detect_address(df, detected_types)

    detected_types = detect_finance(df, detected_types)

    detected_types = detect_identifiers(df, detected_types)

    df = transform_percent(df)
    df = format_df(df, detected_types)
    print(f"\nDF após formatação: \n{df.head(5).to_string(index=False)}")

    # Detecta tipos de colunas e obtém valores únicos para colunas de texto
    detected_types, unique_values_dict = detect_column_type(df, detected_types)

    # Corrige colunas classificadas como 'Número com erro'
    df, detected_types = correct_number(df, detected_types)

    result_df = pd.DataFrame(list(detected_types.items()), columns=['Coluna', 'Tipo'])
    print(f"\n{result_df}\n")
    print(df)

    return df, result_df, unique_values_dict

#---------------------------FAZER O MATCH DAS COLUNAS---------------------------#
def extract_year(value):
    """Extrai os últimos 4 números da string como ano, se possível."""
    match = re.search(r'(\d{4})$', str(value))  # Procura um conjunto de 4 números no final
    return int(match.group(1)) if match else None  # Converte para inteiro ou retorna None

def date_var(formated_new, min_valid_percent=0.8):
    """
        Processa uma Series de datas normalizadas (contendo apenas dígitos no formato DDMMYYYY)
        e retorna a variação (em dias) entre datas consecutivas.

        Parâmetros:
          formated_new: Series com valores de datas contendo apenas dígitos.
          min_valid_percent: Percentual mínimo de dados válidos para continuar a operação.
        """

    # 🔹 1. Imprimir os dados originais
    # print(f"\n📌 Dados originais:\n{formated_new}\n")

    # 🔹 2. Remover valores nulos e converter para string
    valid_dates = formated_new.dropna().astype(str)

    # 🔹 3. Filtrar apenas os valores que têm exatamente 8 caracteres (DDMMYYYY)
    valid_dates_filtered = valid_dates[valid_dates.str.len() == 8]

    # 🔹 4. Verificar a porcentagem de dados válidos
    valid_percent = len(valid_dates_filtered) / len(valid_dates) if len(valid_dates) > 0 else 0

    if valid_percent < min_valid_percent:
        # print(f"⚠️ Apenas {valid_percent:.0%} dos dados estão no formato correto. Abortando operação.")
        return pd.Series(dtype="int64")  # Retorna uma Series vazia

    # print(f"✅ {valid_percent:.0%} dos dados estão corretos ({len(valid_dates_filtered)} valores). Continuando...\n")

    # 🔹 5. Formatar as datas como DD/MM/YYYY
    valid_dates_filtered = valid_dates_filtered.apply(lambda x: f"{x[:2]}/{x[2:4]}/{x[4:]}")
    # print(f"📆 Datas formatadas: \n{valid_dates_filtered}\n")

    # 🔹 6. Converter para datetime
    valid_dates_filtered = pd.to_datetime(valid_dates_filtered, format="%d/%m/%Y", errors="coerce").dropna()
    # print(f"📅 Datas convertidas para datetime: \n{valid_dates_filtered}\n")

    # 🔹 7. Garantir que seja uma Series e ordenar
    valid_dates_filtered = pd.Series(valid_dates_filtered).sort_values(ignore_index=True)
    # print(f"📌 Datas ordenadas: \n{valid_dates_filtered}\n")

    # 🔹 8. Calcular a variação entre valores consecutivos (em dias)
    date_variation = valid_dates_filtered.diff().dt.days
    # print(f"📊 Variação entre datas (dias): \n{date_variation}\n")

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
        name_similarity = 0

        for new_col in new_data.columns:
            if new_col in match:
                continue

            # Verifica se os tipos de dados são compatíveis
            ref_col_type = ref_types.loc[ref_types['Coluna'] == ref_col, 'Tipo'].values[0] if ref_col in ref_types[
                'Coluna'].values else 'Desconhecido'
            new_col_type = new_types.loc[new_types['Coluna'] == new_col, 'Tipo'].values[0] if new_col in new_types[
                'Coluna'].values else 'Desconhecido'

            # Permite match se tipos forem iguais ou se um deles for Null e nomes idênticos
            types_compatible = (ref_col_type == new_col_type)
            null_types = "Null" in [ref_col_type, new_col_type]


            if types_compatible or null_types:  # Apenas compara colunas do mesmo tipo e nulas
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

            if types_compatible and not null_types:
                if ref_col_type == "Data":
                    date_cleaned_new_col = re.sub(r'\b(?:data|de|em|da)\b',
                                                  '', re.sub(r'[.\-]', '', new_col), flags=re.IGNORECASE).lower()

                    date_cleaned_ref_col = re.sub(r'\b(?:data|de|em|da)\b',
                                                  '', re.sub(r'[.\-]', '', ref_col), flags=re.IGNORECASE).lower()
                    name_similarity = SequenceMatcher(None, date_cleaned_new_col, date_cleaned_ref_col).ratio()
                    # if (new_col == 'Atualizado em' or ref_col == 'Data da Última Atualização' or
                    #         ref_col == 'Data de Criação' or new_col == 'Data de Criação'):
                    #     print(f"{date_cleaned_new_col} x {date_cleaned_ref_col}: name similarity = {name_similarity:.2f}")

                data_similarity = 0
                if new_data.get(new_col) is not None and ref_data.get(ref_col) is not None:
                    if ref_col_type == "Texto":
                        # common_values = set(new_data[new_col].dropna().astype(str)) & set(ref_data[ref_col].dropna().astype(str))
                        # total_values = set(new_data[new_col].dropna().astype(str)) | set(ref_data[ref_col].dropna().astype(str))

                        common_values = set(new_data[new_col].dropna().unique()) & set(ref_data[ref_col].dropna().unique())
                        total_values = set(new_data[new_col].dropna().unique()) | set(ref_data[ref_col].dropna().unique())

                        if total_values:
                            data_similarity = len(common_values) / len(total_values)
                            # print(f"TEXTO - Similaridade {new_col} e {ref_col}: {data_similarity}")

                    elif ref_col_type == "Data":
                        formated_new = new_data[new_col].str.replace(r'\D', '', regex=True)
                        formated_ref = ref_data[ref_col].str.replace(r'\D', '', regex=True)

                        year_new = year_evaluation(new_data[new_col])
                        year_ref = year_evaluation(ref_data[ref_col])
                        # print(f"Ano new_data: {year_new}, Ano ref: {year_ref}")

                        # Média das diferenças formatada pelo ano atual
                        data_age = (100 - (abs(year_new - year_ref))) / 100
                        # print(f"Coeficiente ano: {data_age}")

                        variation_new = date_var(formated_new)
                        variation_ref = date_var(formated_ref)

                        if isinstance(variation_new, pd.Series):
                            variation_new = variation_new.mean()
                        if isinstance(variation_ref, pd.Series):
                            variation_ref = variation_ref.mean()

                        scaling_factor = 0.3  # ajusta esse valor conforme necessário
                        variation_diff = abs(variation_new - variation_ref)

                        # Normaliza entre 0 e 1
                        variation_score = 1 - ((variation_diff * scaling_factor) / max(variation_new, variation_ref, 1))
                        # print(f"Variação new: {variation_new}, Variação ref: {variation_ref}, Variação total: {variation_score}")
                        # Combinar idade e variação para calcular similaridade final
                        data_similarity = (data_age * 0.4) + (variation_score * 0.6)
                        # if (new_col == 'Atualizado em' or ref_col == 'Data da Última Atualização' or
                        #         ref_col == 'Data de Criação' or new_col == 'Data de Criação'):
                        #     print(f"{new_col} x {ref_col}: data similarity = {data_similarity:.2f}")

                    else:  #TODO add regra?
                        # data_similarity = 1

                        new_values = set(new_data[new_col].dropna().unique())
                        ref_values = set(ref_data[ref_col].dropna().unique())

                        common_values = new_values & ref_values
                        total_values = new_values | ref_values

                        pd.set_option('display.max_rows', None)  # Exibir todas as linhas

                        # if (new_col == 'Site' or ref_col == 'URL do Site' or
                        #         ref_col == 'Site' or new_col == 'URL do Site'):
                            # print(f"Dados da {new_data[new_col]}: \n{ref_data[ref_col]} ")

                        if total_values:
                            data_similarity = len(common_values) / len(total_values)
                            # print(f"NOT Texto/Data - Similaridade {new_col} e {ref_col}: {data_similarity}")

                    overall_score = (name_similarity * 0.4) + (data_similarity * 0.6)

                    if overall_score > best_score:
                        best_score = overall_score
                        best_match = ref_col
                        best_new_col = new_col  # Armazena a coluna correspondente

        if best_match and best_score >= threshold:
            matched_columns[best_new_col] = best_match
            not_match_new.discard(best_new_col)
            not_match_ref.discard(best_match)
            match.update({best_new_col: best_match})
            print(f"✅ Coluna '{best_new_col}' foi renomeada para '{best_match}' com score {best_score:.2f}")

    print("Correspondência de colunas concluída!\n\nMatchs realizados:")
    for chave, valor in match.items():
        print(f"{chave}: {valor}")
    print(f"\nColunas sem correspondência em {filename1}: {not_match_ref}")
    print(f"Colunas sem correspondência em {filename2}: {not_match_new}\n")

    return matched_columns

#---------------------------TRANSFORMAR OS DADOS DA TABELA NOVA---------------------------#
def validate_data(new_data, matched_columns, ref_unique_values, columns_list):
    """
    Valida os dados em new_data com base nos valores únicos de ref_data.

    Parâmetros:
      new_data: DataFrame que terá os dados validados.
      matched_columns: dicionário no formato {coluna_new_data: coluna_ref_data}.
      unique_values_dict: dicionário onde as chaves são nomes de colunas de ref_data
                          e os valores são os conjuntos (ou listas) dos valores únicos.
      columns_list: lista com os nomes das colunas de referência que devem ser validadas.

    Para cada par de colunas, se a coluna de referência estiver na lista,
    os valores de new_data serão verificados: se algum valor não constar na lista
    de valores únicos de ref_data, ele será substituído por None.
    """
    # Itera sobre cada par de colunas do dicionário de match
    for new_col, ref_col in matched_columns.items():
        # Verifica se a coluna de referência está na lista de validação
        if ref_col in columns_list:
            allowed_values = ref_unique_values.get(ref_col)
            if allowed_values is None:
                print(f"Aviso: Valores únicos para '{ref_col}' não encontrados em unique_values_dict.")
                continue

            # Converte para set para busca mais rápida
            allowed_set = set(allowed_values)

            # Aplica a validação: se o valor não estiver nos permitidos, substitui por None
            new_data[new_col] = new_data[new_col].apply(lambda x: x if x in allowed_set else None)
            # TODO ajustar esse "None"
            print(f"Coluna '{new_col}' validada com base na referência '{ref_col}'.")
    return new_data

# def transform_data(ref_data, new_data, matched_columns):
#     print("\n📝 Iniciando transformação das colunas...")
#
#     # 1. Renomeia as colunas de new_data com base no dicionário:
#     transformed_data = new_data.rename(columns=matched_columns)
#     # print(f"Transformed data (renomear): {transformed_data}")
#
#     # 2. Remover colunas extras em `transformed_data` que não existem em `ref_data`
#     transformed_data = transformed_data[[col for col in ref_data.columns if col in transformed_data.columns]].copy()
#     # print(f"Transformed data (remover): {transformed_data}")
#
#     # 3. Adicionar colunas ausentes em `transformed_data`, preenchendo com "" (ou `None`, se preferir)
#     missing_cols = set(ref_data.columns) - set(transformed_data.columns)
#     for col in missing_cols:
#         transformed_data.loc[:, col] = ""  # ⚠️ Agora usamos .loc para evitar o warning
#
#     # print(f"Transformed data (add): {transformed_data}")
#
#     # 4. Garantir que a ordem das colunas seja a mesma do `ref_data`
#     transformed_data = transformed_data.reindex(columns=ref_data.columns, fill_value="")
#
#     print("Transformação de dados concluída!\n")
#     print(f"Transformed data: \n{transformed_data}")
#     return transformed_data

def transform_data(ref_data, new_data, matched_columns):
    print("\n📝 Iniciando transformação das colunas...")

    # 1. Renomeia as colunas de new_data com base no dicionário:
    print("🔄 Renomeando colunas com base no dicionário de correspondências...")
    renamed_columns = {k: v for k, v in matched_columns.items() if k in new_data.columns}
    print(f"📌 Colunas renomeadas: {renamed_columns}")
    transformed_data = new_data.rename(columns=matched_columns).copy()

    # 2. Remover colunas extras em `transformed_data` que não existem em `ref_data`
    print("🗑️ Removendo colunas que não existem na referência...")
    extra_cols = [col for col in transformed_data.columns if col not in ref_data.columns]
    print(f"❌ Colunas removidas: {extra_cols}")
    transformed_data = transformed_data.loc[:, transformed_data.columns.isin(ref_data.columns)].copy()

    # 3. Adicionar colunas ausentes em `transformed_data`, preenchendo com ""
    print("➕ Adicionando colunas ausentes...")
    missing_cols = set(ref_data.columns) - set(transformed_data.columns)
    print(f"✅ Colunas adicionadas (preenchidas com ''): {missing_cols}")
    for col in missing_cols:
        transformed_data[col] = ""  # Adicionando colunas ausentes

    # 🚨 Verificar colunas duplicadas antes de reindexar
    print("🔍 Verificando colunas duplicadas...")
    duplicated_cols = transformed_data.columns[transformed_data.columns.duplicated()]
    if not duplicated_cols.empty:
        print(f"⚠️ Aviso: Colunas duplicadas detectadas e serão removidas: {list(duplicated_cols)}")
        transformed_data = transformed_data.loc[:, ~transformed_data.columns.duplicated()].copy()
    else:
        print("✅ Nenhuma coluna duplicada encontrada.")

    # 4. Garantir que a ordem das colunas seja a mesma do `ref_data`
    print("🔄 Reorganizando as colunas para manter a mesma ordem da referência...")
    transformed_data = transformed_data.reindex(columns=ref_data.columns, fill_value="").copy()

    print("✅ Transformação de dados concluída!\n")
    return transformed_data

#---------------------------EXECUTAR PROCESSO COMPLETO---------------------------#
def main(ref_data_path, new_data_path, ref_filename, new_filename):
    try:
        ref_path = ref_filename
        new_path = new_filename

        # TODO esse ", dtype=str).dropna(how='all'" talvez tenha que tirar
        print("Carregando arquivos CSV...")
        ref_data = pd.read_csv(ref_data_path, dtype=str).dropna(how='all')
        new_data = pd.read_csv(new_data_path, dtype=str).dropna(how='all')

        print("📊 Analisando tipos de tabela...")
        ref_df = classificar_df(ref_data)
        new_df = classificar_df(new_data)
        if ref_df == new_df:
            print(
                f"\n✅ Comparação entre tipos de tabela OK: \n→ Tabela {ref_path} = {ref_df} \n→ Tabela {new_path} = {new_df}\n")

            # TODO ver se pode manter
            print("Avaliando listas suspensas na tabela de referência")
            ref_data, ref_dd_list = dd_list_columns(ref_data)
            print(f"Lista de colunas drop down: \n{ref_dd_list}")

            print("\n📊 Analisando tipos de dados...")
            # 🔹 Executa a função apenas uma vez e armazena os retornos
            df_ref, ref_types, unique_values_dict_ref = analyze_table(ref_data, ref_path)
            df_new, new_types, _ = analyze_table(new_data, new_path)

            matched_columns = match_columns(df_ref, df_new, ref_types, new_types, ref_path, new_path)

            validated_data = validate_data(df_new, matched_columns, unique_values_dict_ref, ref_dd_list)

            transformed_data = transform_data(df_ref, validated_data, matched_columns)
            # TODO ver se precisa disso
            transformed_data = transformed_data.astype(str)
            # Substituir todas as ocorrências da string "NaN" por valores vazios (sem inplace=True)
            transformed_data.replace("nan", "", inplace=True)

            # Converte o DataFrame para JSON (uma lista de registros)
            json_data = transformed_data.to_json(orient='records')
            print("✅ Dados transformados preparados para API")
            return json_data
        else:
            print(f"Tabelas não correspondem.\nTabela {ref_data} = {ref_df}. Tabela {new_data} = {new_df}")

    except Exception as e:
        return {"error": str(e)}

