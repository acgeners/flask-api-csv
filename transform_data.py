import numpy as np
from sentence_transformers import SentenceTransformer, util
from code_sup import VALID_DDD, months, month_translation
import pandas as pd
import re
from dateutil import parser
from rapidfuzz import process
import time

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
    print("🔍 Detectando e formatando colunas de data...")
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

        # Padrão para números escritos por extenso (ex: "10 milhões", "100 bilhões")
        word_number_pattern = r'(\d+)\s*(milhão|milhões|bilhão|bilhões|mil)'

        # Indicadores de intervalo: "-" ou palavras como "até"
        range_indicators = r'(-|\+|\baté\b|\be\b)'  # "Até 360.000", "360.000 - 4.800.000", etc.

        # Verificações
        has_currency = bool(re.search(currency_symbols, text, re.IGNORECASE))
        has_word_number = bool(re.search(word_numbers, text, re.IGNORECASE))
        has_formatted_number = bool(re.search(number_pattern, text))
        has_range_indicator = bool(re.search(range_indicators, text, re.IGNORECASE))
        has_number_by_words = bool(re.search(word_number_pattern, text))

        # Se tem moeda ou palavra numérica + número, é valor financeiro
        is_value = (has_currency or has_word_number or has_number_by_words) and (
                    has_formatted_number or has_number_by_words)

        # Se também tem um indicador de intervalo, é um range de valores
        is_range = is_value and has_range_indicator

        return is_value, is_range

    for col in df.columns:
        if col in detected_types:
            continue  # Pula colunas já processadas

        # Se a coluna é numérica e o nome tem as palavras 'valor', 'receita', 'faturamento', é considerada "Valor"
        # Lista de palavras-chave indicativas de valor monetário
        keywords = ['valor', 'receita', 'faturamento']

        # Verifica se o nome da coluna contém alguma dessas palavras
        col_lower = col.lower()
        has_keyword = any(kw in col_lower for kw in keywords)

        # Verifica se 90% dos valores não nulos são compostos apenas por dígitos
        def is_valid_number_format(text):
            if not isinstance(text, str):
                return False

            text = text.strip()
            if text.count('.') > 1 or text.count(',') > 1:
                return False

            if not re.fullmatch(r'[\d.,]+', text):
                return False

            return True

        # Verifica se os valores batem com padrão de número formatado
        is_numeric_like = df[col].dropna().astype(str).apply(is_valid_number_format).mean() > 0.9

        # Verifica se os valores são só dígitos (ex: "123456")
        is_numeric = df[col].dropna().astype(str).apply(str.isdigit).mean() > 0.9

        if has_keyword and (is_numeric_like or is_numeric):
            if col == 'Valor':
                print(f"Coluna '{col}': is numerica like - {is_numeric_like}, is numeric - {is_numeric}")
                print(df[col].head())
            detected_types[col] = "Valor"
            print(f"✔ Coluna '{col}' automaticamente classificada como 'Valor' (baseado em nome e conteúdo).")
            continue

        valid_values = df[col].dropna().astype(str).apply(is_financial)
        total_count = df[col].notna().sum()

        value_count = sum(1 for v, r in valid_values if v and not r)  # Apenas valores simples
        range_count = sum(1 for v, r in valid_values if r)  # Apenas ranges de valores

        if col == 'Valor':
            print(f"Coluna '{col}': valid values - {valid_values}, total count - {total_count}, value count - {value_count}")
            print(df[col].head())

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

def detect_num_range(df, detected_types, threshold=0.8):
    print("\n🔍 Detectando colunas de range de números...")

    def is_num_range(text):
        """
        Avalia se um dado representa um número simples ou um range.
        Retorna True se for um número e True se for um range.
        """
        if not isinstance(text, str) or len(text) < 2:
            return False, False  # Retorna duas flags: (é número, é range)

        # Padrões de intervalos numéricos válidos:
        pattern_range = r'^\d+\s*(-|\baté\b)\s*\d+$'  # "10-20", "100 até 200", "50 - 100"
        pattern_open_range = r'^\b(até)\s+\d+$'  # "até 300"
        pattern_plus = r'^\d+\s*\+$'  # "5+"
        float_pattern = r'^-?\d+([.,])\d+$'  # Float simples, ex: "12.3" ou "8,9"

        try:
            has_int_number = int(text)  # Se for um número inteiro válido, não gera erro
            # has_int_number = True
        except ValueError:
            has_int_number = False  # Se der erro ao converter para int, não é número inteiro

        has_float_number = bool(re.search(float_pattern, text))
        has_pattern_range = bool(re.search(pattern_range, text, re.IGNORECASE))
        has_pattern_open_range = bool(re.search(pattern_open_range, text, re.IGNORECASE))
        has_pattern_plus = bool(re.search(pattern_plus, text, re.IGNORECASE))

        # Se tem separador de números, sinal de "+" ou "até" - é um range
        is_range = has_pattern_range or has_pattern_open_range or has_pattern_plus

        # Se tem números inteiros ou float
        is_number = has_int_number or has_float_number

        return is_number, is_range

    for col in df.columns:
        if col in detected_types:
            continue  # Pula colunas já processadas
        # print(f"Coluna sendo avaliada: {col}")
        valid_values = df[col].dropna().astype(str).apply(is_num_range)
        total_count = df[col].notna().sum()

        number_count = sum(1 for v, r in valid_values if v)  # Apenas números
        range_count = sum(1 for v, r in valid_values if r)  # Apenas ranges de números

        if total_count > 0:
            range_ratio = range_count / total_count
            number_ratio = number_count / total_count
            # print(f"Range ratio: {range_ratio}")
            # print(f"Number ratio: {number_ratio}")

            if range_ratio >= threshold or ((range_ratio >= threshold * 0.35) and (range_ratio + number_ratio >= (threshold * 1.1))):
                print(f"• Coluna '{col}' identificada como Range de Números.")
                detected_types[col] = "Número (range)"

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
        return str(int(value))  # Se já for número, retorna como string

    if not isinstance(value, str):
        return value  # Se não for string, retorna sem alterações

    # Verifica se há palavras indicando magnitude numérica (mil, milhão, bilhão)
    word_number_match = re.search(r'(\d+)\s*(milhão|milhões|bilhão|bilhões|mil)', value, re.IGNORECASE)

    if word_number_match:
        num = int(word_number_match.group(1))  # Obtém o número antes da palavra
        multiplier = word_number_match.group(2).lower()  # Obtém a palavra (mil, milhão, bilhão)

        # Define o multiplicador correspondente
        if "milhão" in multiplier or "milhões" in multiplier:
            num *= 1_000_000
        elif "bilhão" in multiplier or "bilhões" in multiplier:
            num *= 1_000_000_000
        elif "mil" in multiplier:
            num *= 1_000

        return str(num)  # Retorna o número corrigido como string

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
    print("\n🔍 Detectando colunas de identificadores: \n→ Site, E-mail, LinkedIn, Instagram\n→ CPF, CNPJ, CNAE, Telefone")

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

            # Contagem de validações personalizadas
            # print("\n📊 Exemplo de valores na coluna CNPJ antes da validação:")
            # print(df["CNPJ"].head(10).tolist())  # Mostra os primeiros 10 CPFs na lista

            cpf_results = values.apply(is_valid_cpf)
            phone_results = values.apply(is_phone_number)
            cnpj_results = values.apply(is_valid_cnpj)
            cnae_results = values.apply(is_valid_cnae)

            cpf_matches = cpf_results.eq("CPF").sum()
            phone_matches = phone_results.eq("Telefone").sum()
            cnpj_matches = cnpj_results.eq("CNPJ").sum()
            cnae_matches = cnae_results.eq("CNAE").sum()

            # Debug para verificar os valores retornados
            # print(f"Resultados CNPJ para a coluna '{col}':\n{cnpj_results.value_counts()}")
            # print(f"Coluna {col}: CNPJ count: {cnpj_matches}, total: {total_values}")

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
    print("\n🔍 Formatando colunas - fazendo alterações necessárias...")

    def clean_column(value):
        if isinstance(value, str):
            if not value.strip():
                return value  # Retorna o valor sem alterações se for vazio ou conter só espaços
            return re.sub(r'\D', '', value)
        return value

    # Criar uma cópia do DataFrame para evitar modificar o original
    df_formated = df.copy()

    format_columns = [
        col for col in df_formated.select_dtypes(include=["object"]).columns
        if detected_types.get(col, "") in ("Telefone", "CPF", "CNPJ", "CNAE")  # Retorna "" se col não existir
    ]

    format_value_columns = [
        col for col in df_formated.select_dtypes(include=["object"]).columns
        if detected_types.get(col, "") == "Valor"
    ]

    format_range_columns = [
        col for col in df_formated.select_dtypes(include=["object"]).columns
        if detected_types.get(col, "") == "Range de valores"
    ]

    # Aplicar a formatação apenas nessas colunas
    print("Formatando colunas de identificadores...")
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

    print("Formatando colunas de valores...")
    for col in format_value_columns:
        df_formated[col] = df_formated[col].map(format_value)
        # print(f"Coluna {col}: \n{df_formated[col]}")

    print("Formatando colunas com range de valores...")
    for col in format_range_columns:
        detected_types[col] = "Valor (range)"

    print(f"✅ Colunas formatadas: {format_columns}, {format_value_columns}")

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
        if detected_types[col] == "Texto" or detected_types[col].endswith(" (range)"):
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

    # Configura pandas para exibir todas as colunas na saída
    # pd.set_option('display.max_columns', None)  # Exibe todas as colunas
    # pd.set_option('display.width', 200)  # Ajusta a largura do terminal para evitar truncamento
    # Configura o pandas para exibir todas as linhas e colunas
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
    detected_types = detect_num_range(df, detected_types)

    df = transform_percent(df)
    df = format_df(df, detected_types)
    # print(f"\nDF após formatação: \n{df.head(5).to_string(index=False)}")

    # Detecta tipos de colunas e obtém valores únicos para colunas de texto
    detected_types, unique_values_dict = detect_column_type(df, detected_types)

    # Corrige colunas classificadas como 'Número com erro'
    df, detected_types = correct_number(df, detected_types)

    print(f"\nDF após formatação: \n{df.head(5).to_string(index=False)}")

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

def describe_data_column(col_data, col_name, max_exemplos=5):
    valores = col_data.dropna().astype(str).unique()
    exemplos = sorted(valores)[:max_exemplos]  # sempre os mesmos
    exemplos_str = ", ".join(exemplos)
    return f"Coluna: {col_name}. Tipo: número. Exemplos: {exemplos_str}"


def match_columns(ref_data, new_data, ref_types, new_types, filename1, filename2, threshold=0.59):
    match = {}
    not_match_new = set(new_data.columns)
    not_match_ref = set(ref_data.columns)
    candidates = []
    model = SentenceTransformer('paraphrase-MiniLM-L3-v2')
    # model = SentenceTransformer('all-MiniLM-L6-v2')

    # Calcula o embedding de cada coluna
    ref_embeddings = {col: model.encode(col, convert_to_tensor=True) for col in ref_data.columns}
    new_embeddings = {col: model.encode(col, convert_to_tensor=True) for col in new_data.columns}

    # Cria os textos descritivos pra cada coluna, gera embeddings e calcula similaridade semântica entre os dados
    ref_data_desc = {
        col: model.encode(describe_data_column(ref_data[col], col), convert_to_tensor=True)
        for col in ref_data.columns
    }
    new_data_desc = {
        col: model.encode(describe_data_column(new_data[col], col), convert_to_tensor=True)
        for col in new_data.columns
    }

    print("\nIniciando correspondência de colunas...")

    for ref_col in ref_data.columns:
        for new_col in new_data.columns:
            if new_col in match:
                continue

            ref_embedding = ref_embeddings[ref_col]
            new_embedding = new_embeddings[new_col]

            name_similarity = util.cos_sim(ref_embedding, new_embedding).item()
            # TODO isso não deveria considerar

            # Verifica se os tipos de dados são compatíveis, ignorando " (range)"
            ref_col_type = ref_types.loc[ref_types['Coluna'] == ref_col, 'Tipo'].values[0] if ref_col in ref_types[
                'Coluna'].values else 'Desconhecido'
            new_col_type = new_types.loc[new_types['Coluna'] == new_col, 'Tipo'].values[0] if new_col in new_types[
                'Coluna'].values else 'Desconhecido'

            # Limpa espaços e sufixo " (range)" apenas para comparação
            ref_col_type = ref_col_type.strip()
            new_col_type = new_col_type.strip()
            ref_col_type_cleaned = ref_col_type.replace(" (range)", "")
            new_col_type_cleaned = new_col_type.replace(" (range)", "")

            types_compatible = ref_col_type_cleaned == new_col_type_cleaned
            null_types = "Null" in [ref_col_type_cleaned, new_col_type_cleaned]
            if types_compatible or null_types:  # Apenas compara colunas do mesmo tipo e nulas
                #  or value_number
                print(f"{new_col} x {ref_col}: name similarity = {name_similarity:.2f}")

                if name_similarity >= 0.98 and (null_types or ref_col_type.endswith("(range)")): #TODO deixa isso?
                    overall_score = 1.0
                    candidates.append((ref_col, new_col, overall_score))
                    print(
                        f"✅ Coluna '{new_col}' adicionada como match direto de '{ref_col}' por similaridade de nome = 1")

            if types_compatible and not null_types:
            #  or value_number)
                data_similarity = 0
                if new_col in new_data.columns and ref_col in ref_data.columns:
                    if ref_col_type == "Data":
                        formated_new = new_data[new_col].str.replace(r'\D', '', regex=True)
                        formated_ref = ref_data[ref_col].str.replace(r'\D', '', regex=True)

                        year_new = year_evaluation(new_data[new_col])
                        year_ref = year_evaluation(ref_data[ref_col])

                        # Média das diferenças formatada pelo ano atual
                        data_age = (100 - (abs(year_new - year_ref))) / 100

                        variation_new = date_var(formated_new)
                        variation_ref = date_var(formated_ref)

                        if isinstance(variation_new, pd.Series):
                            variation_new = variation_new.mean()
                        if isinstance(variation_ref, pd.Series):
                            variation_ref = variation_ref.mean()

                        scaling_factor = 0.3  # ajustar esse valor conforme necessário
                        variation_diff = abs(variation_new - variation_ref)

                        # Normaliza entre 0 e 1
                        variation_score = 1 - ((variation_diff * scaling_factor) / max(variation_new, variation_ref, 1))
                        # Combinar idade e variação para calcular similaridade final
                        data_similarity = (data_age * 0.4) + (variation_score * 0.6)

                    elif ref_col_type_cleaned == "Valor":
                        data_similarity = 1

                    else:  #TODO add regra?
                        # Calcula a similaridade entre os dados e suas descrições (baseado em amostragem)
                        ref_data_emb = ref_data_desc[ref_col]
                        new_data_emb = new_data_desc[new_col]

                        data_similarity = util.cos_sim(ref_data_emb, new_data_emb).item()

                    print(f"{new_col} x {ref_col}: data similarity = {data_similarity:.2f}")

                if name_similarity == 1:
                    overall_score = (name_similarity * 0.7) + (data_similarity * 0.3)
                else:
                    overall_score = (name_similarity * 0.25) + (data_similarity * 0.75)
                    # TODO verificar os pesos

                print(f"Score final: {ref_col} x {new_col} = {overall_score}")

                if overall_score >= threshold:
                    candidates.append((ref_col, new_col, overall_score))

    # ✅ Após o loop: resolve matches com maior score, sem repetir colunas
    used_new_cols = set()
    matched_columns = {}

    candidates.sort(key=lambda x: x[2], reverse=True)

    for ref_col, new_col, score in candidates:
            if ref_col not in matched_columns and new_col not in used_new_cols:
                matched_columns[ref_col] = new_col
                used_new_cols.add(new_col)
                not_match_new.discard(new_col)
                not_match_ref.discard(ref_col)
                print(f"✅ Coluna '{new_col}' foi renomeada para '{ref_col}' com score {score:.2f}")

    # Impressão final
    print("\n\nCorrespondência de colunas concluída!\n\nMatchs realizados (definitivos):")
    for ref_col, new_col in matched_columns.items():
        print(f"{ref_col}: {new_col}")

    if not_match_ref:
        print(f"\nColunas sem correspondência em {filename1}: {not_match_ref}")
    if not_match_new:
        print(f"Colunas sem correspondência em {filename2}: {not_match_new}\n")

    return matched_columns

#---------------------------TRANSFORMAR OS DADOS DA TABELA NOVA---------------------------#
def format_range(value):
    if not isinstance(value, str) or len(value) < 2:
        return None, None  # Retorna valores nulos se o dado for inválido

    # Remover símbolos de moeda, espaços e caracteres não numéricos (exceto "-" e "+")
    clean_value = re.sub(r'[^\d\-,+]', '', value)

    # Se o formato for "Até R$360.000"
    if "Até" in value or clean_value.startswith('-'):
        min_value = 0  # Define o mínimo como 0
        max_value = re.sub(r'\D', '', clean_value)  # Mantém apenas números no máximo
        max_value = int(max_value)
        return int(min_value), max_value if max_value else None

    # Se for um range no formato "R$360.000 - R$4.800.000"
    elif '-' in clean_value:
        min_value, max_value = clean_value.split('-')
        min_value = re.sub(r'\D', '', min_value)
        max_value = re.sub(r'\D', '', max_value)
        min_value = int(min_value) if min_value else None
        max_value = int(max_value) if max_value else None
        return min_value, max_value

    # Se for um valor aberto como "R$10.000.000.000 +"
    elif "+" in clean_value:
        min_value = re.sub(r'\D', '', clean_value)
        min_value = int(min_value) if min_value else None
        max_value = 999999999999999  # Define o máximo fixo como 999999999999999
        return min_value, max_value

    return None, None  # Caso não caia em nenhum formato esperado


def transform_value(new_data, matched_columns, unique_values, ref_list, ref_types):
    # # Filtrar os itens que possuem "Valor (range)" na coluna "Tipo"
    # print(f"Matched columns: {matched_columns}. \nmatched_columns:: {type(matched_columns)}")
    # print(f"Unique values: {unique_values}. \nunique_values: {type(unique_values)}")
    # print(f"Ref list: {ref_list}. \nref_list: {type(ref_list)}")
    # print(f"Ref types: {ref_types}. \nref_types: {type(ref_types)}")

    print("Transformando valores tipo range")
    range_columns = ref_types[ref_types['Tipo'].isin(['Valor (range)', 'Número (range)'])]['Coluna']
    # print(f"Range columns: {range_columns}")

    # print(f"Colunas: {range_columns}")

    result_df = pd.DataFrame()

    for column in range_columns:
        if column in ref_list:
            # print(f"Coluna {column} está na lista de drop down")
            # print(f"Coluna {column} presente na lista de colunas")
            # Buscar os valores associados em unique_values
            # print(unique_values)
            if column in unique_values:
                # print(f"Coluna {column} está no dicionario")
                # print(f"Coluna {column} presente no dicionario de valores únicos")
                # unique_df = pd.DataFrame(unique_values[column], columns=[column])
                unique_df = pd.DataFrame(unique_values.get(column, []), columns=[column])
                # print(f"Unique df: {unique_df}")

                # Se unique_df estiver vazio, imprimir aviso
                if unique_df.empty:
                    print(f"⚠️ Aviso: Nenhum valor encontrado em unique_values para {column}. Pulando...")
                    continue

                    # Criar colunas de mínimo e máximo
                unique_df[[f"{column} - Min", f"{column} - Max"]] = (
                    unique_df[column]
                    .apply(lambda x: format_range(x))  # Retorna (Min, Max)
                    .apply(pd.Series)
                )
                # print(f"Unique df min e max: {unique_df}")
                # # Criar colunas de mínimo e máximo
                # unique_df[[f"{column} - Min", f"{column} - Max"]] = unique_df[column].apply(lambda x: format_range(x)).apply(pd.Series)
                # print(f"DF com os valores transformados: \n{unique_df}")

                # Se `format_range` não estiver funcionando corretamente, pode retornar colunas vazias
                if unique_df[[f"{column} - Min", f"{column} - Max"]].isnull().all().all():
                    print(f"⚠️ Aviso: Todos os valores em {column} - Min e {column} - Max são NaN.")
                    continue  # Evita continuar se os valores forem inválidos

                # Armazenar o resultado
                # result_df = pd.concat([result_df, unique_df], axis=0)
                # print(f"DF resultante: \n{result_df}")

                result_df = pd.concat([result_df, unique_df], axis=0).reset_index(drop=True)
                # print(f"Result df: {result_df}")
                # print(f"✔️ Intervalos para {column} gerados:\n{unique_df}")

            if column in matched_columns:
                # print(f"Coluna {column} presente no dicionario de matches")
                mapped_column = matched_columns[column]
                if mapped_column in new_data:
                    # print(f"🔹 Aplicando transformação na coluna correspondente: {mapped_column}")

                    # ✅ Verificar se as colunas existem antes de acessá-las
                    if f"{column} - Min" not in result_df.columns or f"{column} - Max" not in result_df.columns:
                        print(f"⚠️ Aviso: Colunas {column} - Min e {column} - Max não encontradas. Pulando...")
                        continue  # Evita erro de KeyError

                    # Converter para numérico
                    def convert_to_number(value):
                        # Substitui vírgula por ponto para conversão correta
                        value = str(value).replace(",", ".")

                        # Verifica se é um número puro
                        if value.replace(".", "", 1).isdigit():  # Permite apenas um ponto decimal
                            return float(value)

                        # Se for um intervalo "X-Y", calcular a média
                        if "-" in value:
                            parts = value.split("-")
                            try:
                                num1 = float(parts[0].strip())
                                num2 = float(parts[1].strip())
                                return (num1 + num2) / 2  # Média dos dois números
                            except ValueError:
                                return np.nan  # Caso algum valor não seja numérico, retorna NaN

                        return np.nan  # Caso não seja possível converter

                    new_data[mapped_column] = new_data[mapped_column].apply(convert_to_number)

                    # print(f"New data: {new_data[mapped_column]}")

                    def map_value(x):
                        if pd.notnull(x):  # Evita erros com valores nulos
                            row = result_df[
                                (result_df[f"{column} - Min"] <= x) &
                                (result_df[f"{column} - Max"] >= x)
                                ]
                            # print(f"Row: {row}")
                            return row[column].values[0] if not row.empty else None
                        return None

                    # 🔹 Substituir a coluna original
                    new_data[mapped_column] = new_data[mapped_column].apply(map_value)
                    # print(f"New data: \n{new_data[mapped_column]}")
                    # print(f"✔️ Transformação aplicada para {mapped_column}")
                    # print(new_data)

    return new_data

def transform_data(ref_data, new_data, matched_columns):
    print("\n📝 Iniciando transformação das colunas...")

    # 1. Renomeia as colunas de new_data com base no dicionário:
    print("🔄 Renomeando colunas com base no dicionário de correspondências...")
    renamed_columns = {v: k for k, v in matched_columns.items() if v in new_data.columns}
    print(f"📌 Colunas renomeadas: {renamed_columns}")
    transformed_data = new_data.rename(columns=renamed_columns).copy()
    print(f"dados transformados de new_data: \n{transformed_data}")

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

def validate_data(new_data, matched_columns, ref_unique_values, columns_list, threshold=0.6):
    for ref_col, new_col in matched_columns.items():
        if ref_col in columns_list:
            allowed_values = ref_unique_values.get(ref_col, [])

            if not allowed_values or not isinstance(allowed_values, list):
                print(f"Aviso: Valores únicos para '{ref_col}' não encontrados ou inválidos.")
                continue

            # Garante que allowed_values seja uma lista de strings
            allowed_values = [str(val).strip() for val in allowed_values]

            def find_best_match(value):
                if pd.isna(value) or value == "nan":  # Se for NaN, retorna vazio
                    return ""
                value = str(value).strip()  # Converte para string e remove espaços extras

                # Obtém a melhor correspondência e a pontuação de similaridade
                best_match, score = process.extractOne(value, allowed_values)

                return best_match if score >= threshold else value  # Retorna o original se não for próximo o suficiente

            # Verifica se a coluna existe no DataFrame antes de aplicar a correção
            if new_col in new_data.columns:
                new_data[new_col] = new_data[new_col].astype(str).apply(find_best_match)
                print(f"Coluna '{new_col}' validada com base na referência '{ref_col}'.")
            else:
                print(f"Aviso: Coluna '{new_col}' não encontrada no DataFrame.")

    return new_data

#---------------------------EXECUTAR PROCESSO COMPLETO---------------------------#
def main(ref_data_path, new_data_path, ref_filename, new_filename):
    try:
        ref_path = ref_filename
        new_path = new_filename

        start_time = time.time()

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
            df_new = transform_value(df_new, matched_columns, unique_values_dict_ref, ref_dd_list, ref_types)

            validated_data = validate_data(df_new, matched_columns, unique_values_dict_ref, ref_dd_list)

            transformed_data = transform_data(df_ref, validated_data, matched_columns)
            # TODO ver se precisa disso
            transformed_data = transformed_data.astype(str)
            # Substituir todas as ocorrências da string "NaN" por valores vazios (sem inplace=True)
            transformed_data.replace("nan", "", inplace=True)
            transformed_data.replace("None", "", inplace=True)

            # Converte o DataFrame para JSON (uma lista de registros)
            json_data = transformed_data.to_json(orient='records')
            print("✅ Dados transformados preparados para API")

            end_time = time.time()

            elapsed_time = end_time - start_time
            print(f"⏱️ Tempo de execução: {elapsed_time:.2f} segundos")
            return json_data
        else:
            print(f"Tabelas não correspondem.\nTabela {ref_data} = {ref_df}. Tabela {new_data} = {new_df}")

    except Exception as e:
        return {"error": str(e)}