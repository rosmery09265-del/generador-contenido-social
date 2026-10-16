import os
import requests
import glob
import subprocess
import asyncio
import time
import re
import random
from google import genai
from dotenv import load_dotenv
from faster_whisper import WhisperModel
from openai import OpenAI

load_dotenv()

# Credenciales y APIs protegidas mediante variables de entorno (.env)
GEMINI_KEY = os.getenv('GEMINI_API_KEY')
PEXELS_KEY = os.getenv('PEXELS_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

client_openai = OpenAI(api_key=OPENAI_API_KEY)
client_ia = genai.Client(api_key=GEMINI_KEY)

def buscar_videos_pexels(query, cantidad=20):
    print(f"🔍 Searching Pexels clips for: '{query}'...")
    
    api_key = PEXELS_KEY
    if not api_key:
        print("❌ Error: PEXELS_API_KEY no está configurada en las variables de entorno.")
        return []

    headers = {"Authorization": api_key}

    # FILTRO DE EMERGENCIA: Limpiar búsquedas genéricas de dinero
    palabras_prohibidas = ["money", "cash", "wealth", "rich", "dollar", "dinero"]
    if any(prohibida in query.lower() for prohibida in palabras_prohibidas):
        KEYWORDS_PROFESIONALES = [
            "business charts", "stock market screen", "investment planning",
            "office brainstorming", "financial growth", "urban architecture modern"
        ]
        query = random.choice(KEYWORDS_PROFESIONALES)
        print(f"⚠️ Query genérica detectada. Cambiada estratégicamente a: '{query}'")

    url = f"https://api.pexels.com/videos/search?query={query}&per_page={cantidad}"
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        video_paths = []
        if "videos" in data:
            for v in data["videos"]:
                for file in v.get("video_files", []):
                    if file.get("link"):
                        video_paths.append(file["link"])
                        break
        return video_paths
    except Exception as e:
        print(f"❌ Error al consultar Pexels: {e}")
        return []

def generar_metadatos_sociales(tema, archivo_meta_destino):
    print(f"✍️ Generating viral copy, titles and hashtags for {archivo_meta_destino}...")
    prompt = f"""
    You are an expert social media manager for Instagram Reels and TikTok in the US financial niche.
    Based on the topic '{tema}', generate the copy for the post.

    Return EXACTLY this template and nothing else:
    TITLE: [A magnetic, short title with emojis]
    COPY: [A high-retention caption explaining the value of the video in 2 sentences. End with a question to trigger comments to boost engagement.]
    HASHTAGS: [Include 8 high-traffic viral tags for US audience like #foryou #wealthtips #investing]
    """
    espera = 10
    for intento in range(3):
        try:
            res = client_ia.models.generate_content(model='gemini-2.5-flash', contents=prompt)
            with open(archivo_meta_destino, "w", encoding="utf-8") as f:
                f.write(res.text.strip())
            print(f"📝 {archivo_meta_destino} successfully created.")
            return
        except Exception as e:
            if "429" in str(e) or "Resource" in str(e):
                print(f"⚠️ Gemini Rate Limit in Metadata. Retrying in {espera}s...")
                time.sleep(espera + random.uniform(1, 3))
                espera *= 2
            else:
                print(f"⚠️ Error in Metadata: {e}")
                break

def obtener_duracion_audio(audio_path):
    comando = [
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', audio_path
    ]
    try:
        resultado = subprocess.run(comando, capture_output=True)
        return float(resultado.stdout.strip())
    except Exception as e:
        print(f"⚠️ Error probing audio duration: {e}")
        return 60.0

def generar_subtitulos_estilo_capcut(audio_path, output_ass_path):
    print("🎨 Generating dynamic CapCut-style subtitles...")
    try:
        import whisper
        model = whisper.load_model("tiny")
        result = model.transcribe(audio_path, fp16=False, language="en")

        with open(output_ass_path, "w", encoding="utf-8") as f:
            f.write("[Script Info]\nScriptType: v4.00+\nPlayResX: 720\nPlayResY: 1280\n\n")
            f.write("[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, BackColour, OutlineColour, Bold, Italic, Alignment, BorderStyle, Outline, Shadow, MarginL, MarginR, MarginV, Encoding\n")
            f.write("Style: Default,Arial,32,&H00FFFFFF,&H00000000,&H00000000,-1,0,2,1,3,0,10,10,150,1\n\n")
            f.write("[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")

            for segment in result.get("segments", []):
                start = segment["start"]
                end = segment["end"]

                def format_time(seconds):
                    h = int(seconds // 3600)
                    m = int((seconds % 3600) // 60)
                    s = int(seconds % 60)
                    ms = int(round((seconds % 1) * 100))
                    return f"{h}:{m:02d}:{s:02d}.{ms:02d}"

                f.write(f"Dialogue: 0,{format_time(start)},{format_time(end)},Default,,0,0,0,,{segment['text'].strip()}\n")
        print("✨ Subtitles (.ass) successfully generated.")
    except Exception as e:
        print(f"⚠️ Error creating subtitles, creating a dummy file: {e}")
        with open(output_ass_path, "w") as f: f.write("")

def generar_audio_premium(texto_guion, nombre_archivo_salida):
    print(f"🎙️ Generando locución premium con OpenAI TTS...")
    try:
        response = client_openai.audio.speech.create(
            model="tts-1",
            voice="fable",
            input=texto_guion
        )
        response.stream_to_file(nombre_archivo_salida)
        print(f"✅ Audio guardado como: {nombre_archivo_salida}")
        return nombre_archivo_salida
    except Exception as e:
        print(f"❌ Error en OpenAI TTS: {e}")
        return None

def procesar_video_multicanal_premium(video_paths, guion_texto, archivo_video, dia_actual):
    nombre_audio_salida = f"assetflow_{dia_actual.lower()}.mp3"
    print(f"🎙️ Generando locución dinámica para {dia_actual.upper()}...")
    archivo_audio = generar_audio_premium(guion_texto, nombre_audio_salida)

    if not archivo_audio:
        print(f"❌ Error crítico: No se pudo generar el audio premium. Deteniendo este video.")
        return False

    duracion_total = obtener_duracion_audio(archivo_audio)

    carpeta_musica = "musica_fondo"
    canciones = glob.glob(os.path.join(carpeta_musica, "*.mp3"))
    archivo_musica = None
    tiene_fondo = False

    if not canciones:
        print(f"⚠️ No se encontró música en '{carpeta_musica}'. El video será sin fondo.")
    else:
        archivo_musica = random.choice(canciones)
        print(f"🎵 Canción viral seleccionada: {os.path.basename(archivo_musica)}")

    comando = ['ffmpeg', '-y']
    for video in video_paths:
        comando.extend(['-i', video])
    comando.extend(['-i', archivo_audio])
    if archivo_musica:
        comando.extend(['-i', archivo_musica])

    num_videos = len(video_paths)
    indice_voz = num_videos
    indice_fondo = num_videos + 1

    escalado = "".join([f"[{i}:v]scale=720:1280,setdar=9/16,setsar=1,trim=duration=3[v{i}_prep];" for i in range(num_videos)])
    inputs_fragmentos = "".join([f"[v{i}_prep]" for i in range(num_videos)])
    concat_filtro = f"{escalado}{inputs_fragmentos}concat=n={num_videos}:v=1:a=0[v_raw];"

    loop_y_subtitulos = f"[v_raw]loop=loop=-1:size=32767:start=0,subtitles=subtitulos.ass[v_sub]"

    if canciones:
        print(f"🎵 {len(canciones)} canciones encontradas. Usando música de fondo.")
        tiene_fondo = True
    else:
        print("⚠️ No se encontraron canciones en 'musica_fondo'. El video será sin fondo.")
        tiene_fondo = False

    if tiene_fondo:
        audio_entrada = '[a_mix]'
        filtro_audio = (
            f";[{indice_voz}:a]volume=1.6[a_voz];"
            f"[{indice_fondo}:a]volume=0.12[a_fondo];"
            f"[a_voz][a_fondo]amix=inputs=2:duration=first[a_mix]"
        )
    else:
        audio_entrada = f'[{indice_voz}:a]'
        filtro_audio = ""

    duracion_total = obtener_duracion_audio(archivo_audio)
    filtro_completo = f"{concat_filtro}{loop_y_subtitulos}{filtro_audio}"

    argumentos_mapeo = [
        '-filter_complex', filtro_completo,
        '-map', '[v_sub]',
        '-map', audio_entrada
    ]

    comando.extend(argumentos_mapeo)
    nombre_salida_video = f"{dia_actual}.mp4"
    comando.extend(['-t', str(duracion_total), '-preset', 'veryfast', nombre_salida_video])

    try:
        print("🎬 Iniciando renderizado de alta retención...")
        subprocess.run(comando, check=True)
        print(f"✨ ¡VIDEO PROFESIONAL GENERADO!: '{nombre_salida_video}'")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en el proceso de renderizado: {e}")
        return False

if __name__ == "__main__":
    archivo_estrategia = "estrategia.txt"

    if not os.path.exists(archivo_estrategia):
        print(f"⚠️ '{archivo_estrategia}' not found. Creating a bulletproof default financial strategy...")
        temas_defecto = [
            "Why standard savings accounts destroy your purchasing power through inflation",
            "How to utilize Dollar-Cost Averaging into blue-chip stocks to build long-term safety",
            "The magic of compound interest hidden inside premium dividend stocks",
            "Why the wealthy never keep cash in the bank and where they move it",
            "How to build a bulletproof two-stock portfolio to outpace Wall Street"
        ]
        with open(archivo_estrategia, "w", encoding="utf-8") as f:
            for t in temas_defecto:
                f.write(f"{t}\n")

    with open(archivo_estrategia, "r", encoding="utf-8") as f:
        secuencia_temas = [linea.strip() for linea in f.readlines() if linea.strip()]

    dias = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    print(f"🎯 Strategy loaded! Processing {len(secuencia_temas)} videos for the week.")
    print("--------------------------------------------------")

    for indice, tema_del_dia in enumerate(secuencia_temas):
        if indice >= len(dias):
            break

        dia_actual = dias[indice]
        print(f"\n🎬 PROCESSING VIDEO FOR {dia_actual.upper()}: '{tema_del_dia}'")

        archivo_video = f"assetflow_{dia_actual.lower()}_video.mp4"
        archivo_meta = f"assetflow_{dia_actual.lower()}_meta.txt"

        video_paths = buscar_videos_pexels(tema_del_dia)
        generar_metadatos_sociales(tema_del_dia, archivo_meta)
        
        print(f"✍️ Generating extended 60-second script in English with Gemini...")
        prompt_guion = f"""
        Write a voiceover script for a short video (Reel/Short) based on this topic: '{tema_del_dia}'.
        STRICT REQUIREMENTS:
        - The script MUST be written entirely in ENGLISH.
        - It must be between 130 and 150 words long so it lasts approximately 60 seconds when spoken.
        - Use a dynamic, engaging, and persuasive tone.
        - Start directly with a strong hook, deliver 3 quick key points, and end with a call to action.
        - Return ONLY the spoken text. Do not include any introductions, brackets, scene descriptions, or narrator tags.
        """

        try:
            respuesta_ia = client_ia.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt_guion
            )
            guion_texto = respuesta_ia.text.strip()
            print(f"   Guion generado con éxito ({len(guion_texto.split())} palabras en inglés).")
        except Exception as e:
            print(f"⚠️ Falló Gemini al extender el guion: {e}. Usando respaldo rápido.")
            guion_texto = tema_del_dia
            
        procesar_video_multicanal_premium(video_paths, guion_texto, archivo_video, dia_actual)
        print(f"✅ Saved Assets for {dia_actual}: Created '{archivo_video}' and '{archivo_meta}'")

        print("⏳ Sleeping 45 seconds to guarantee API rate limits reset...")
        time.sleep(45)

    print("\n🏁 CONGRATULATIONS: Your weekly content sequence has been successfully fully rendered.")
    if os.path.exists("historial_videos.txt"):
        os.remove("historial_videos.txt")
        print("♻️ Weekly video cache cleared. Ready for next week's clean batch!")
