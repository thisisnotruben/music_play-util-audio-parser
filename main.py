import os
import mutagen
import json
from dotenv import load_dotenv 
import tarfile
from mutagen.easyid3 import EasyID3
from pathlib import Path


class Main:

    def __init__(self, scan_dir: str, dest_data_path: str, dest_tar_path: str):
        self.scan_dir = scan_dir
        self.dest_data_path = dest_data_path
        self.dest_tar_path = dest_tar_path

    def run(self):
        data = {'data': {}}
        cover_path_files: list[str] = []

        for (dirpath, _, filenames) in os.walk(self.scan_dir):
            for file_name in filenames:
                full_path = os.path.join(dirpath, file_name)
                audio_metadata = self.get_metadata2(full_path)
                
                artist_name = audio_metadata.pop('artistName')
                album_name = audio_metadata.pop('album')

                if len(artist_name) == 0 \
                or len(album_name) == 0 \
                or len(audio_metadata['name']) == 0:
                    continue

                elif artist_name in data['data'].keys():

                    if album_name in data['data'][artist_name]['albums'].keys():
                        data['data'][artist_name]['albums'][album_name].append(audio_metadata)
                    else:
                        data['data'][artist_name]['albums'][album_name] = [audio_metadata]

                else:
                    data['data'][artist_name] = {
                        'albums': {
                            album_name: [audio_metadata]
                        }
                    }

        with open(self.dest_data_path, 'w',) as f:
            f.write(json.dumps(data, indent='\t'))

        with tarfile.open(self.dest_tar_path, 'w:tar') as tar_file:
            for cover_path in cover_path_files:
                tar_file.add(cover_path)

    def get_metadata(self, file_path: str) -> dict:
        data = {
            'name': '',
            'artistName': '',
            'album': '',
            'genre': '',
            'length': 0,
            'coverPath': '',
            'audioPath': os.path.join(*list(Path(file_path).parts[5:])),
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

if __name__ == "__main__":
    load_dotenv()
    args_labels = ['SCAN_DIR', 'DEST_DATA_PATH', 'DEST_TAR_PATH']
    args = [os.getenv(label) for label in args_labels]

    Main(*args).run()
