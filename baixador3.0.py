import os
import re
import json
from datetime import datetime
from typing import Optional, Dict, List
from concurrent.futures import ThreadPoolExecutor
from pytube import Search, YouTube
from pytube.exceptions import PytubeError
import yt_dlp
import warnings
from tqdm import tqdm
import eyed3
import tkinter as tk
from tkinter import ttk
import pygame
import threading
import time
from PIL import Image, ImageTk
import requests
from io import BytesIO

# Suprimir warnings
warnings.filterwarnings("ignore")

class MusicInfo:
    def __init__(self, title: str, url: str, duration: int, thumbnail: str = None):
        self.title = title
        self.url = url
        self.duration = duration
        self.thumbnail = thumbnail

from youtubesearchpython import VideosSearch

class MusicDownloader:
    def __init__(self):
        self.diretorio_downloads = os.path.join(os.path.expanduser("~"), "Downloads", "Musicas")
        self.arquivo_historico = os.path.join(self.diretorio_downloads, "historico_downloads.json")
        self.criar_diretorio()
        self.historico = self.carregar_historico()

    def criar_diretorio(self):
        """Cria o diretório de downloads se não existir."""
        if not os.path.exists(self.diretorio_downloads):
            os.makedirs(self.diretorio_downloads)
            print(f"Diretório criado: {self.diretorio_downloads}")

    def carregar_historico(self) -> List[Dict]:
        """Carrega o histórico de downloads do arquivo JSON."""
        if os.path.exists(self.arquivo_historico):
            try:
                with open(self.arquivo_historico, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print("Erro ao carregar histórico. Criando novo arquivo.")
                return []
        return []

    def salvar_historico(self):
        """Salva o histórico de downloads no arquivo JSON."""
        with open(self.arquivo_historico, 'w', encoding='utf-8') as f:
            json.dump(self.historico, f, ensure_ascii=False, indent=2)

    def buscar_musica(self, query: str) -> Optional[Dict]:
        """Busca uma música no YouTube usando youtube-search-python."""
        try:
            search = VideosSearch(query, limit=1)
            results = search.result()

            if not results['result']:
                print("Nenhum resultado encontrado.")
                return None

            video = results['result'][0]
            return {
                'title': video['title'],
                'url': video['link'],
                'duration': video['duration'],
                'thumbnail': video['thumbnails'][0]['url'],
            }
        except Exception as e:
            print(f"Erro ao buscar música: {str(e)}")
            return None

    # Restante do código da classe...
    
    def baixar_musica(self, url: str) -> Optional[str]:
        """Baixa uma música a partir da URL do YouTube."""
        try:
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '320',
                }],
                'outtmpl': os.path.join(self.diretorio_downloads, '%(title)s.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
                'progress_hooks': [lambda d: self._mostrar_progresso(d)],
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                titulo = info.get('title', 'Música desconhecida')
                arquivo = os.path.join(self.diretorio_downloads, f"{titulo}.mp3")
                
                # Adicionar metadados ao MP3
                self._adicionar_metadados(arquivo, info)
                
                # Registrar no histórico
                self.historico.append({
                    'title': titulo,
                    'url': url,
                    'data': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                    'arquivo': arquivo
                })
                self.salvar_historico()
                
                print(f"\nDownload concluído: {titulo}")
                print(f"Salvo em: {arquivo}")
                return arquivo
                
        except Exception as e:
            print(f"Erro ao baixar música: {str(e)}")
            return None
    
    def _mostrar_progresso(self, d):
        """Callback para mostrar progresso do download."""
        if d['status'] == 'downloading':
            p = re.search(r'(\d+\.\d+)%', d.get('_percent_str', '0%'))
            if p:
                progresso = float(p.group(1))
                print(f"Baixando: {progresso:.1f}%", end='\r')
    
    def _adicionar_metadados(self, arquivo: str, info: Dict):
        """Adiciona metadados ao arquivo MP3."""
        try:
            audiofile = eyed3.load(arquivo)
            if audiofile and audiofile.tag:
                audiofile.tag.title = info.get('title', 'Desconhecido')
                audiofile.tag.artist = info.get('uploader', 'Desconhecido')
                audiofile.tag.save()
        except Exception as e:
            print(f"Aviso: Não foi possível adicionar metadados: {str(e)}")
    
    def baixar_playlist(self, url: str):
        """Baixa todas as músicas de uma playlist."""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if 'entries' not in info:
                    print("Esta URL não parece ser uma playlist válida.")
                    return
                
                total_musicas = len(info['entries'])
                print(f"\nPlaylist encontrada: {info.get('title', 'Desconhecida')}")
                print(f"Total de músicas: {total_musicas}")
                
                confirmacao = input("Deseja prosseguir com o download? (s/n): ").lower()
                if confirmacao != 's':
                    print("Download cancelado.")
                    return
                
                print("\nIniciando downloads...")
                
                # Baixar músicas com ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=3) as executor:
                    for i, entry in enumerate(tqdm(info['entries'], desc="Progresso da playlist")):
                        if entry:
                            video_url = f"https://www.youtube.com/watch?v={entry['id']}"
                            executor.submit(self.baixar_musica, video_url)
                
                print("\nDownload da playlist concluído!")
                
        except Exception as e:
            print(f"Erro ao baixar playlist: {str(e)}")

class MusicPlayer:
    def __init__(self, root, music_downloader):
        self.root = root
        self.downloader = music_downloader
        self.current_song_index = 0
        self.is_playing = False
        self.is_muted = False
        self.previous_volume = 0.8
        self.playlist = []
        
        # Inicializar pygame para reprodução de áudio
        pygame.mixer.init()
        
        self.setup_ui()
        self.load_available_songs()
        
        # Iniciar thread para atualizar a barra de progresso
        self.update_thread = threading.Thread(target=self.update_progress_thread, daemon=True)
        self.update_thread.start()
    
    def setup_ui(self):
        """Configura a interface do player de música."""
        self.root.title("Music Player")
        self.root.geometry("800x600")
        self.root.minsize(800, 600)
        
        # Frame principal
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Frame superior - Controles do player
        player_frame = ttk.Frame(main_frame, padding=5)
        player_frame.pack(fill=tk.X, pady=10)
        
        # Informações da música atual
        self.current_song_frame = ttk.Frame(player_frame)
        self.current_song_frame.pack(fill=tk.X, pady=10)
        
        # Placeholder para a capa do álbum
        self.album_cover_label = ttk.Label(self.current_song_frame)
        self.album_cover_label.pack(side=tk.LEFT, padx=10)
        self.set_default_album_cover()
        
        # Informações da música
        song_info_frame = ttk.Frame(self.current_song_frame)
        song_info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        
        self.song_title_label = ttk.Label(song_info_frame, text="Nenhuma música selecionada", font=("Arial", 12, "bold"))
        self.song_title_label.pack(anchor=tk.W)
        
        # Barra de progresso
        progress_frame = ttk.Frame(player_frame)
        progress_frame.pack(fill=tk.X, pady=5)
        
        self.current_time_label = ttk.Label(progress_frame, text="0:00")
        self.current_time_label.pack(side=tk.LEFT)
        
        self.progress_bar = ttk.Scale(progress_frame, from_=0, to=100, orient=tk.HORIZONTAL, command=self.seek_position)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.total_time_label = ttk.Label(progress_frame, text="0:00")
        self.total_time_label.pack(side=tk.LEFT)
        
        # Controles de reprodução
        controls_frame = ttk.Frame(player_frame)
        controls_frame.pack(pady=10)
        
        ttk.Button(controls_frame, text="⏮", width=3, command=self.prev_song).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="⏪", width=3, command=self.rewind).pack(side=tk.LEFT, padx=5)
        self.play_button = ttk.Button(controls_frame, text="▶", width=5, command=self.toggle_play)
        self.play_button.pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="⏩", width=3, command=self.forward).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="⏭", width=3, command=self.next_song).pack(side=tk.LEFT, padx=5)
        
        # Controle de volume
        volume_frame = ttk.Frame(player_frame)
        volume_frame.pack(pady=5)
        
        self.mute_button = ttk.Button(volume_frame, text="🔊", width=3, command=self.toggle_mute)
        self.mute_button.pack(side=tk.LEFT, padx=5)
        
        self.volume_slider = ttk.Scale(volume_frame, from_=0, to=100, orient=tk.HORIZONTAL, command=self.set_volume,length=100)
          # Configura o comprimento do slider
        self.volume_slider.set(80)  # Volume inicial
        self.volume_slider.pack(side=tk.LEFT, padx=5)  # Removido o argumento width
        
        # Notebook para gerenciar abas
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Aba de Playlist
        playlist_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(playlist_frame, text="Playlist")
        
        # Lista de reprodução
        playlist_scroll = ttk.Scrollbar(playlist_frame)
        playlist_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.playlist_listbox = tk.Listbox(playlist_frame, font=("Arial", 10), 
                                          selectbackground="#4682B4",
                                          activestyle="none",
                                          height=15)
        self.playlist_listbox.pack(fill=tk.BOTH, expand=True)
        self.playlist_listbox.config(yscrollcommand=playlist_scroll.set)
        playlist_scroll.config(command=self.playlist_listbox.yview)
        self.playlist_listbox.bind("<Double-1>", self.play_selected)
        
        # Aba de Busca/Download
        download_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(download_frame, text="Baixar Músicas")
        
        # Interface de busca
        search_frame = ttk.Frame(download_frame)
        search_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(search_frame, text="Buscar música:").pack(side=tk.LEFT, padx=5)
        self.search_entry = ttk.Entry(search_frame, width=40)
        self.search_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.search_entry.bind("<Return>", lambda e: self.search_music())
        
        ttk.Button(search_frame, text="Buscar", command=self.search_music).pack(side=tk.LEFT, padx=5)
        
        # Resultado da busca
        self.search_result_frame = ttk.LabelFrame(download_frame, text="Resultado da busca", padding=10)
        self.search_result_frame.pack(fill=tk.X, pady=10)
        
        self.result_label = ttk.Label(self.search_result_frame, text="Use a caixa de busca acima para encontrar músicas")
        self.result_label.pack(pady=20)
        
        self.download_button = ttk.Button(self.search_result_frame, text="Baixar", command=self.download_current_search, state=tk.DISABLED)
        self.download_button.pack(pady=5)
        
        # Aba de histórico
        history_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(history_frame, text="Histórico")
        
        # Lista de histórico
        history_scroll = ttk.Scrollbar(history_frame)
        history_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.history_listbox = tk.Listbox(history_frame, font=("Arial", 10), 
                                        selectbackground="#4682B4",
                                        activestyle="none",
                                        height=15)
        self.history_listbox.pack(fill=tk.BOTH, expand=True)
        self.history_listbox.config(yscrollcommand=history_scroll.set)
        history_scroll.config(command=self.history_listbox.yview)
        self.history_listbox.bind("<Double-1>", self.play_from_history)
        
        self.refresh_history_button = ttk.Button(history_frame, text="Atualizar Histórico", command=self.load_history)
        self.refresh_history_button.pack(pady=10)
        
        # Inicialização
        self.current_search_result = None
        self.load_history()
    
    def set_default_album_cover(self):
        """Define uma imagem padrão para a capa do álbum."""
        blank_image = Image.new('RGB', (100, 100), color=(200, 200, 200))
        photo = ImageTk.PhotoImage(blank_image)
        self.album_cover_label.config(image=photo)
        self.album_cover_label.image = photo  # Guardar referência
    
    def set_album_cover(self, thumbnail_url):
        """Define a capa do álbum a partir de uma URL."""
        try:
            response = requests.get(thumbnail_url)
            img = Image.open(BytesIO(response.content))
            img = img.resize((100, 100), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.album_cover_label.config(image=photo)
            self.album_cover_label.image = photo  # Guardar referência
        except Exception:
            self.set_default_album_cover()

    def load_available_songs(self):
        """Carrega as músicas disponíveis no diretório de downloads."""
        self.playlist = []
        self.playlist_listbox.delete(0, tk.END)
        
        if not os.path.exists(self.downloader.diretorio_downloads):
            return
        
        for file in os.listdir(self.downloader.diretorio_downloads):
            if file.endswith(".mp3"):
                filepath = os.path.join(self.downloader.diretorio_downloads, file)
                self.playlist.append(filepath)
                self.playlist_listbox.insert(tk.END, os.path.basename(file))
    
    def load_history(self):
        """Carrega o histórico de downloads."""
        self.downloader.historico = self.downloader.carregar_historico()
        self.history_listbox.delete(0, tk.END)
        
        for item in self.downloader.historico:
            self.history_listbox.insert(tk.END, f"{item['title']} - {item['data']}")
    
    def play_selected(self, event=None):
        """Reproduz a música selecionada na playlist."""
        selection = self.playlist_listbox.curselection()
        if not selection:
            return
        
        self.current_song_index = selection[0]
        self.play_current_song()
    
    def play_from_history(self, event=None):
        """Reproduz uma música do histórico."""
        selection = self.history_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        if index < len(self.downloader.historico):
            filepath = self.downloader.historico[index]['arquivo']
            if os.path.exists(filepath):
                # Verificar se a música já está na playlist
                if filepath in self.playlist:
                    self.current_song_index = self.playlist.index(filepath)
                else:
                    # Adicionar à playlist e reproduzir
                    self.playlist.append(filepath)
                    self.playlist_listbox.insert(tk.END, os.path.basename(filepath))
                    self.current_song_index = len(self.playlist) - 1
                
                self.play_current_song()
            else:
                tk.messagebox.showinfo("Arquivo não encontrado", 
                                      "O arquivo da música não existe mais no diretório de downloads.")
    
    def play_current_song(self):
        """Reproduz a música atual."""
        if not self.playlist or self.current_song_index >= len(self.playlist):
            return
        
        filepath = self.playlist[self.current_song_index]
        if not os.path.exists(filepath):
            tk.messagebox.showinfo("Arquivo não encontrado", "O arquivo da música não existe.")
            return
        
        # Destacar a música atual na playlist
        self.playlist_listbox.select_clear(0, tk.END)
        self.playlist_listbox.selection_set(self.current_song_index)
        self.playlist_listbox.see(self.current_song_index)
        
        # Parar qualquer reprodução atual
        pygame.mixer.music.stop()
        
        # Reproduzir a nova música
        pygame.mixer.music.load(filepath)
        pygame.mixer.music.set_volume(self.volume_slider.get() / 100)
        pygame.mixer.music.play()
        
        # Atualizar interface
        self.is_playing = True
        self.play_button.config(text="⏸")
        self.song_title_label.config(text=os.path.basename(filepath))
        
        # Tentar obter metadados
        try:
            audiofile = eyed3.load(filepath)
            if audiofile and audiofile.tag:
                title = audiofile.tag.title or os.path.basename(filepath)
                artist = audiofile.tag.artist or "Artista desconhecido"
                self.song_title_label.config(text=f"{title} - {artist}")
        except Exception:
            pass
        
        # Atualizar tempo total
        sound = pygame.mixer.Sound(filepath)
        duration = sound.get_length()
        self.progress_bar.config(to=duration)
        self.total_time_label.config(text=self.format_time(duration))
    
    def toggle_play(self):
        """Alterna entre reproduzir e pausar."""
        if not self.playlist:
            return
        
        if self.is_playing:
            pygame.mixer.music.pause()
            self.play_button.config(text="▶")
            self.is_playing = False
        else:
            if pygame.mixer.music.get_pos() == -1:  # Nenhuma música carregada
                self.play_current_song()
            else:
                pygame.mixer.music.unpause()
                self.play_button.config(text="⏸")
                self.is_playing = True
    
    def next_song(self):
        """Reproduz a próxima música na playlist."""
        if not self.playlist:
            return
        
        self.current_song_index = (self.current_song_index + 1) % len(self.playlist)
        self.play_current_song()
    
    def prev_song(self):
        """Reproduz a música anterior na playlist."""
        if not self.playlist:
            return
        
        self.current_song_index = (self.current_song_index - 1) % len(self.playlist)
        self.play_current_song()
    
    def rewind(self):
        """Retrocede 10 segundos."""
        if not self.is_playing:
            return
        
        current_pos = pygame.mixer.music.get_pos() / 1000  # em segundos
        new_pos = max(0, current_pos - 10)
        pygame.mixer.music.rewind()
        pygame.mixer.music.set_pos(new_pos)
    
    def forward(self):
        """Avança 10 segundos."""
        if not self.is_playing:
            return
        
        current_pos = pygame.mixer.music.get_pos() / 1000  # em segundos
        sound = pygame.mixer.Sound(self.playlist[self.current_song_index])
        duration = sound.get_length()
        new_pos = min(duration, current_pos + 10)
        pygame.mixer.music.rewind()
        pygame.mixer.music.set_pos(new_pos)
    
    def seek_position(self, value):
        """Define a posição da música na barra de progresso."""
        if not self.is_playing:
            return
        
        value = float(value)
        pygame.mixer.music.rewind()
        pygame.mixer.music.set_pos(value)
    
    def set_volume(self, value):
        """Define o volume da reprodução."""
        volume = float(value) / 100
        pygame.mixer.music.set_volume(volume)
        
        # Atualizar ícone de volume
        if volume == 0:
            self.mute_button.config(text="🔇")
            self.is_muted = True
        else:
            self.mute_button.config(text="🔊")
            self.is_muted = False
            self.previous_volume = volume
    
    def toggle_mute(self):
        """Alterna entre mudo e com som."""
        if self.is_muted:
            # Restaurar volume anterior
            self.volume_slider.set(self.previous_volume * 100)
            pygame.mixer.music.set_volume(self.previous_volume)
            self.mute_button.config(text="🔊")
            self.is_muted = False
        else:
            # Salvar volume atual e mutar
            self.previous_volume = pygame.mixer.music.get_volume()
            pygame.mixer.music.set_volume(0)
            self.volume_slider.set(0)
            self.mute_button.config(text="🔇")
            self.is_muted = True
    
    def format_time(self, seconds):
        """Formata o tempo em segundos para minutos:segundos."""
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}:{secs:02d}"
    
    def update_progress_thread(self):
        """Thread para atualizar a barra de progresso."""
        while True:
            if self.is_playing and pygame.mixer.music.get_busy():
                # Posição atual em milissegundos
                current_pos = pygame.mixer.music.get_pos() / 1000
                
                if current_pos >= 0:
                    # Atualizar barra de progresso
                    self.progress_bar.set(current_pos)
                    
                    # Atualizar label de tempo atual
                    self.current_time_label.config(text=self.format_time(current_pos))
            
            # Verificar se a música terminou
            if self.is_playing and not pygame.mixer.music.get_busy():
                self.next_song()
                
            time.sleep(0.1)
    
    def search_music(self):
        """Busca uma música no YouTube."""
        query = self.search_entry.get().strip()
        if not query:
            return
        
        # Limpar resultados anteriores
        for widget in self.search_result_frame.winfo_children():
            if widget not in (self.result_label, self.download_button):
                widget.destroy()
        
        self.result_label.config(text="Buscando...")
        self.download_button.config(state=tk.DISABLED)
        self.current_search_result = None
        
        # Executar busca em segundo plano
        def do_search():
            result = self.downloader.buscar_musica(query)
            
            # Atualizar UI no thread principal
            self.root.after(0, lambda: self.update_search_result(result))
        
        threading.Thread(target=do_search, daemon=True).start()
    
    def update_search_result(self, result):
        """Atualiza a interface com o resultado da busca."""
        if not result:
            self.result_label.config(text="Nenhum resultado encontrado.")
            return
        
        self.current_search_result = result
        
        # Atualizar label com informações
        self.result_label.config(text=f"Música encontrada: {result['title']}\nDuração: {result['duration']} segundos")
        
        # Atualizar botão de download
        self.download_button.config(state=tk.NORMAL)
        
        # Mostrar thumbnail se disponível
        if result.get('thumbnail'):
            try:
                response = requests.get(result['thumbnail'])
                img = Image.open(BytesIO(response.content))
                img = img.resize((120, 90), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                thumbnail_label = ttk.Label(self.search_result_frame, image=photo)
                thumbnail_label.image = photo  # Guardar referência
                thumbnail_label.pack(before=self.download_button)
            except Exception:
                pass
    
    def download_current_search(self):
        """Baixa a música atualmente em exibição nos resultados."""
        if not self.current_search_result:
            return
        
        self.download_button.config(state=tk.DISABLED)
        self.result_label.config(text="Baixando... Por favor, aguarde.")
        
        # Baixar em segundo plano
        def do_download():
            filepath = self.downloader.baixar_musica(self.current_search_result['url'])
            
            # Atualizar UI no thread principal
            self.root.after(0, lambda: self.download_completed(filepath))
        
        threading.Thread(target=do_download, daemon=True).start()
    
    def download_completed(self, filepath):
        """Atualiza a interface após o download ser concluído."""
        if filepath:
            self.result_label.config(text="Download concluído com sucesso!")
            
            # Atualizar playlist
            self.load_available_songs()
            
            # Atualizar histórico
            self.load_history()
        else:
            self.result_label.config(text="Erro ao realizar o download.")
        
        self.download_button.config(state=tk.NORMAL)


def main():
    """Função principal do programa."""
    root = tk.Tk()
    downloader = MusicDownloader()
    
    # Inicializar o player
    player = MusicPlayer(root, downloader)
    
    # Iniciar loop principal da interface
    root.mainloop()


if __name__ == "__main__":
    main()
    
