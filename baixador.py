from pytube import YouTube

def baixar_audio(url_video):
  """
  Função para baixar o áudio de um vídeo do YouTube.

  Args:
    url_video (str): A URL do vídeo do YouTube.

  Returns:
    str: O caminho para o arquivo MP3 baixado.
  """

  try:
    # Cria um objeto YouTube a partir da URL do vídeo
    youtube = YouTube(url_video)

    # Obtém o stream de áudio com a melhor taxa de bits
    audio_stream = youtube.streams.filter(only_audio=True).order_by('abr').desc().first()

    # Define o nome do arquivo de saída
    nome_arquivo = f"{youtube.title}.mp3"

    # Baixa o arquivo de áudio
    audio_stream.download(filename=nome_arquivo)

    print(f"Áudio baixado com sucesso: {nome_arquivo}")

    return nome_arquivo

  except Exception as e:
    print(f"Erro ao baixar o áudio: {e}")
    return None

# URL do vídeo de exemplo
#url_video = "https://www.youtube.com/watch?v=W9zFXOEESy0"
url_video = input("Digite entre aspas duplas a url do vídeo:\n")
# Baixa o áudio do vídeo
baixar_audio(url_video)
