import os
import mutagen
import json
from dotenv import load_dotenv
import logging
import tarfile
from mutagen.easyid3 import EasyID3
from pathlib import Path
import subprocess
import sys


class Main:

    logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    def __init__(self, scan_dir: str, dest_data_path: str, dest_tar_path: str):
        self.scan_dir = scan_dir
        self.dest_data_path = dest_data_path
        self.dest_tar_path = dest_tar_path

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

                    if os.path.isfile(cover_art_path):
                        cover_path_files[file_path_key] = cover_art_path
                    else:
                        cover_art_path = ''

                if os.path.isfile(cover_art_path):
                    cover_art_path = os.path.join(*list(Path(cover_art_path).parts[4:]))

                if artist_name in data['data'].keys():

                    if data['data'][artist_name]['albums'][-1]['name'] == album_name:
                        data['data'][artist_name]['albums'][-1]['songs'].append(audio_metadata)
                    else:
                        data['data'][artist_name]['albums'].append({
                            'name': album_name,
                            'coverPath': cover_art_path,
                            'songs': [audio_metadata]
                        })

                else:
                    data['data'][artist_name] = {
                        'albums': [{
                            'name': album_name,
                            'coverPath': cover_art_path,
                            'songs': [audio_metadata],
                        }]
                    }

        logging.info('Writing data to csv.')
        with open(self.dest_data_path, 'w',) as f:
            f.write(json.dumps(data, indent='\t'))

        logging.info('Writing data to tar file.')
        with tarfile.open(self.dest_tar_path, 'w:tar') as tar_file:
            for cover_path in cover_path_files.values():
                tar_file.add(cover_path)

    def get_metadata(self, file_path: str) -> dict:
        data = {
            'name': '',
            'artistName': '',
            'album': '',
            'genre': '',
            'length': 0,
            'audioPath': os.path.join(*list(Path(file_path).parts[4:])),
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
    args_labels = ['SCAN_DIR', 'DEST_DATA_PATH', 'DEST_TAR_PATH']
    args = [os.getenv(label) for label in args_labels]

    Main(*args).run()
