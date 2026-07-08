import os

# Configurações
ARQUIVO_SAIDA = "PROJETO_CONSOLIDADO.txt"
PASTAS_IGNORADAS = {'venv', 'venv_qlib', 'venv_omnis', 'qlib', '.git', '__pycache__', '.github', 'docs'}
EXTENSOES_PERMITIDAS = {'.py', '.yaml', '.yml', '.toml', '.txt', '.md', '.rst'}

def consolidar_codigo():
    print(f"Iniciando varredura em: {os.getcwd()}")
    
    with open(ARQUIVO_SAIDA, 'w', encoding='utf-8') as f_out:
        for raiz, diretorios, arquivos in os.walk('.'):
            # Filtra as pastas ignoradas para o os.walk não entrar nelas
            diretorios[:] = [d for d in diretorios if d not in PASTAS_IGNORADAS]
            
            for nome_arquivo in arquivos:
                extensao = os.path.splitext(nome_arquivo)[1].lower()
                
                if extensao in EXTENSOES_PERMITIDAS:
                    caminho_completo = os.path.join(raiz, nome_arquivo)
                    rel_path = os.path.relpath(caminho_completo, '.')
                    
                    print(f"Copiando: {rel_path}")
                    
                    # Escreve um cabeçalho para identificar o arquivo no TXT
                    f_out.write(f"\n{'='*80}\n")
                    f_out.write(f" ARQUIVO: {rel_path}\n")
                    f_out.write(f"{'='*80}\n\n")
                    
                    try:
                        with open(caminho_completo, 'r', encoding='utf-8', errors='ignore') as f_in:
                            f_out.write(f_in.read())
                            f_out.write("\n")
                    except Exception as e:
                        f_out.write(f"Erro ao ler arquivo: {str(e)}\n")

    print(f"\nPronto! Todo o código foi consolidado em: {ARQUIVO_SAIDA}")

if __name__ == "__main__":
    consolidar_codigo()