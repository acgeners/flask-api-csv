import pandas as pd
import re

# Listas de palavras positivas e negativas
palavras_positivas = ['ref', 'modelo', 'referencia', 'padrão']
palavras_negativas = ['despadronizado', 'nao padrao', 'não padrao']

def limpar_nome(nome):
    """
    Converte o nome para minúsculas e substitui sublinhados e hífens por espaços.
    """
    nome = nome.lower()
    # Substitui _ e - por espaços
    nome = nome.replace('_', ' ').replace('-', ' ')
    return nome

def pontuar_nome_arquivo(nome):
    """
    Pontua o nome do arquivo somando 1 para cada ocorrência de uma palavra positiva
    (considerando limites de palavra) e subtraindo 1 para cada palavra negativa.
    """
    nome_limpo = limpar_nome(nome)
    score = 0
    # Pontua cada ocorrência de palavras positivas
    for palavra in palavras_positivas:
        if re.search(r'\b' + re.escape(palavra) + r'\b', nome_limpo):
            score += 1
    # Subtrai pontos para palavras negativas
    for palavra in palavras_negativas:
        if re.search(r'\b' + re.escape(palavra) + r'\b', nome_limpo):
            score -= 1
    return score

# Exemplos de nomes de arquivos
arquivo1 = "MODELO _ ENTIDADE - NEGÓCIO - TABELA.csv"
arquivo2 = "MODELO Despadronizado _ ENTIDADE - NEGÓCIO - TABELA.csv"

score1 = pontuar_nome_arquivo(arquivo1)
score2 = pontuar_nome_arquivo(arquivo2)

# Se os scores forem iguais, verifica explicitamente a presença de palavras positivas
if score1 == score2:
    tem_pos_arquivo1 = any(re.search(r'\b' + re.escape(palavra) + r'\b', limpar_nome(arquivo1))
                            for palavra in palavras_positivas)
    tem_pos_arquivo2 = any(re.search(r'\b' + re.escape(palavra) + r'\b', limpar_nome(arquivo2))
                            for palavra in palavras_positivas)
    if tem_pos_arquivo1 and not tem_pos_arquivo2:
        score1 += 1
    elif tem_pos_arquivo2 and not tem_pos_arquivo1:
        score2 += 1

# Define qual é o arquivo de referência com base na pontuação
if score1 > score2:
    file_ref_name = arquivo1
    new_ref_name = arquivo2
elif score2 > score1:
    file_ref_name = arquivo2
    new_ref_name = arquivo1
else:
    # Se ainda assim os scores forem iguais, pode ser necessário um fallback
    print("Ambos os arquivos têm pontuação igual. Verifique os nomes manualmente.")
    file_ref_name = arquivo1  # Exemplo de fallback
    new_ref_name = arquivo2

# Carrega os arquivos CSV usando Pandas
file_ref = pd.read_csv(file_ref_name)
new_ref = pd.read_csv(new_ref_name)

print("Arquivo de referência:", file_ref_name)
print("Arquivo novo:", new_ref_name)
