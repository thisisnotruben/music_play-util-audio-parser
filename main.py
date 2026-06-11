import os
import mutagen
import json
from dotenv import load_dotenv
import logging
import tarfile
from mutagen.easyid3 import EasyID3
from pathlib import Path
import subprocess
# https://deepwiki.com/resemble-ai/chatterbox/2-getting-started
import torchaudio as ta
from chatterbox.tts import ChatterboxTTS


class Main:

    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(levelname)s]  %(message)s',
                        handlers=[
                            logging.FileHandler('.log'),
                            logging.StreamHandler(),
                        ])

    def __init__(self, scan_dir: str, dest_data_path: str, dest_tar_path: str, dest_tar_audio_path: str):
        self.scan_dir = scan_dir
        self.dest_data_path = dest_data_path
        self.dest_tar_path = dest_tar_path
        self.dest_tar_audio_path = dest_tar_audio_path
        self.audio_dir = 'music'

    def format_upload_path(self, s: str) -> str:
        return os.path.join(*list(Path(s).parts[4:])).replace(' ', '-')

    def run(self):

        data = {'data': {}}
        cover_path_files = {}

        logging.info('Collecting info.')
        for (dirpath, _, filenames) in os.walk(self.scan_dir):
            for file_name in filenames:
                full_path = os.path.join(dirpath, file_name)
                audio_metadata = self.get_metadata(full_path)
                artist_name = audio_metadata.pop('artistName')
                album_name = audio_metadata.pop('album')

                if len(artist_name) == 0 \
                or len(album_name) == 0 \
                or len(audio_metadata['name']) == 0:
                    continue

                file_path_key: str = artist_name + album_name
                cover_art_path: str = cover_path_files.get(file_path_key, '')
                if len(cover_art_path) == 0:
                    for file_name in os.listdir(dirpath):
                        match (os.path.splitext(file_name)[1]).lower():
                            case '.jpg'| '.jpeg' | '.png':
                                cover_art_path = os.path.join(dirpath, file_name)
                        if len(cover_art_path) > 0:
                            break

                    if len(cover_art_path) == 0:
                        cover_art_path = self.get_image(full_path)

                    upload_path = ''
                    if os.path.isfile(cover_art_path):
                        cover_path_files[file_path_key] = cover_art_path
                        upload_path = self.format_upload_path(cover_art_path)

                if artist_name in data['data'].keys():

                    if data['data'][artist_name]['albums'][-1]['name'] == album_name:
                        data['data'][artist_name]['albums'][-1]['songs'].append(audio_metadata)
                    else:
                        data['data'][artist_name]['albums'].append({
                            'name': album_name,
                            'coverPath': upload_path,
                            'songs': [audio_metadata]
                        })

                else:
                    data['data'][artist_name] = {
                        'albums': [{
                            'name': album_name,
                            'coverPath': upload_path,
                            'songs': [audio_metadata],
                        }]
                    }

        logging.info('Writing data to csv.')
        with open(self.dest_data_path, 'w',) as f:
            f.write(json.dumps(data, indent='\t'))

        logging.info('Writing data to tar file.')
        with tarfile.open(self.dest_tar_path, 'w:tar') as tar_file:
            for file_path in cover_path_files.values():
                tar_file.add(file_path, self.format_upload_path(file_path))

    def getAudio(self):
        data: dict = {}
        with open(self.dest_data_path) as f:
            data = json.load(f)

        logging.info("Generating audio.")
        model = ChatterboxTTS.from_pretrained(device='cuda')

        for artist_name in data['data']:
            for album_data in data['data'][artist_name]['albums']:
                for song in album_data['songs']:

                    file_path = os.path.splitext(song['audioPath'])[0] + '.wav'
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    if os.path.isfile(file_path):
                        continue

                    text =  artist_name + ' ' + album_data['name'] + ' ' + song['name']
                    logging.info('Generating audio for: [%s].' % text)
                    wav = model.generate(text)

                    logging.info('Saving audio to: [%s].' % file_path)
                    ta.save(file_path, wav, model.sr)

        generated_files = []
        for (dirpath, _, filenames) in os.walk(self.audio_dir):
            for file_name in filenames:

                file_path = os.path.join(dirpath, file_name)
                if file_path.endswith('.ogg'):
                    continue
                coverted_file_path = os.path.splitext(file_path)[0] + '.ogg'

                logging.info('Coverting to wav -> ogg [%s].' % file_path)
                response = subprocess.run(['ffmpeg', '-i', file_path, '-acodec', 'libvorbis', '-b:a', '16K', coverted_file_path, '-y'])
                if response.returncode == 0:
                    generated_files.append(coverted_file_path)
                else:
                    logging.warning('Trouble converting: [%s].' % file_path)

        if os.path.isdir(self.audio_dir):
            logging.info('Writing audio files to tar file.')

            with tarfile.open(self.dest_tar_audio_path, 'w:gz') as tar_file:
                for file_path in generated_files:
                    tar_file.add(file_path)

    def get_metadata(self, file_path: str) -> dict:
        data = {
            'name': '',
            'artistName': '',
            'album': '',
            'genre': '',
            'length': 0,
            'audioPath': os.path.splitext(self.format_upload_path(file_path))[0] + '.ogg',
        }

        try:
            audio = EasyID3(file_path)
            keys = audio.keys()
            for key in keys:
                match key:
                    case 'title':
                        data['name'] = audio[key][0]
                    case 'artist' | 'albumartist':
                        data['artistName'] = audio[key][0]
                    case 'album' | 'genre':
                        data[key] = audio[key][0]
                    case 'length':
                        data[key] = int(audio[key][0])
        except mutagen.MutagenError:
            pass
        finally:
            return data

    def get_image(self, file_path: str) -> str:
        match (os.path.splitext(file_path)[1]).lower():
            case '.jpg'| '.jpeg' | '.png':
                return file_path
            case '.mp3':
                logging.info('Running ffmpeg: [%s].' % file_path)

                cover_file_path = os.path.join(os.path.dirname(file_path), 'cover.jpg')
                res = subprocess.run(['ffmpeg', '-i', file_path, '-an', '-vcodec', 'copy', cover_file_path], capture_output=True, text=True)
                if res.returncode != 0:
                    logging.warning('Running ffmpeg failed: [%s].' % file_path)
                else:
                    return cover_file_path
        return ''

if __name__ == "__main__":
    load_dotenv()
    args_labels = ['SCAN_DIR', 'DEST_DATA_PATH', 'DEST_TAR_PATH', 'DEST_TAR_AUDIO_PATH']
    args = [os.getenv(label) for label in args_labels]

    main = Main(*args)
    main.run()
    main.getAudio()
